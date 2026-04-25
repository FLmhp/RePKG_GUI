import ast
import csv
import datetime
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any

import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
RUNTIME_DIR = os.path.join(PROJECT_ROOT, "runtime")
CONFIG_FILE = os.path.join(RUNTIME_DIR, "config.json")
ERROR_LOG_FILE = os.path.join(RUNTIME_DIR, "errors.txt")
INFO_CSV_FILE = os.path.join(RUNTIME_DIR, "info.csv")
LOG_FILE = os.path.join(RUNTIME_DIR, "logs.txt")
LEGACY_CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")
LEGACY_ERROR_LOG_FILE = os.path.join(PROJECT_ROOT, "errors.txt")
LEGACY_INFO_CSV_FILE = os.path.join(PROJECT_ROOT, "info.csv")
LEGACY_LOG_FILE = os.path.join(PROJECT_ROOT, "logs.txt")
REPKG_EXECUTABLE = os.path.join(PROJECT_ROOT, "RePKG.exe")
WORKSHOP_APP_ID = "431960"
DEFAULT_OUTPUT_PATH = "./output"
DEFAULT_BATCH_EXTRACT_WORKERS = 0
MAX_BATCH_EXTRACT_WORKERS = 32
DEFAULT_CONFIG = {
    "steam_path": "",
    "output_path": DEFAULT_OUTPUT_PATH,
    "batch_extract_workers": DEFAULT_BATCH_EXTRACT_WORKERS,
}
CONFIG_KEYS = tuple(DEFAULT_CONFIG.keys())
INFO_FIELDS = ["preview", "tags", "title", "type", "visibility", "file", "id"]
PREVIEW_FILENAMES = ("preview.jpg", "preview.jpeg", "preview.gif", "preview.png")
LOCAL_OUTPUT_MODE = "分别输出至源文件所在文件夹"
SHARED_OUTPUT_MODE = "在指定文件夹中集中输出"
SEPARATE_OUTPUT_MODE = "在指定文件夹中输出至单独的文件夹"


@dataclass
class AppConfig:
    steam_path: str = ""
    output_path: str = DEFAULT_OUTPUT_PATH
    batch_extract_workers: int = DEFAULT_BATCH_EXTRACT_WORKERS

    def to_dict(self):
        return {
            "steam_path": self.steam_path,
            "output_path": self.output_path,
            "batch_extract_workers": self.batch_extract_workers,
        }


@dataclass
class WallpaperInfo:
    preview: str = ""
    tags: list[str] | None = None
    title: str = ""
    type: str = ""
    visibility: str = ""
    file: str = ""
    id: str = ""

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

    def to_csv_row(self):
        return {
            "preview": self.preview,
            "tags": serialize_tags(self.tags),
            "title": self.title,
            "type": self.type,
            "visibility": self.visibility,
            "file": self.file,
            "id": self.id,
        }


@dataclass
class ExtractionOptions:
    steam_path: str
    output_path: str
    output_mode: str
    not_convert_tex_to_image: bool = False
    use_wallpaper_name_as_subdir: bool = True
    copy_project_json_and_preview: bool = False
    overwrite_files: bool = True


def log_success(message):
    ensure_runtime_dir()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} - SUCCESS: {message}\n")


def log_error(message):
    ensure_runtime_dir()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(ERROR_LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} - {message}\n")


def _write_json_file(path, data):
    parent_dir = os.path.dirname(path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def ensure_runtime_dir():
    os.makedirs(RUNTIME_DIR, exist_ok=True)


def migrate_legacy_runtime_files():
    legacy_to_runtime = (
        (LEGACY_CONFIG_FILE, CONFIG_FILE),
        (LEGACY_ERROR_LOG_FILE, ERROR_LOG_FILE),
        (LEGACY_INFO_CSV_FILE, INFO_CSV_FILE),
        (LEGACY_LOG_FILE, LOG_FILE),
    )

    for legacy_path, runtime_path in legacy_to_runtime:
        if os.path.exists(legacy_path) and not os.path.exists(runtime_path):
            shutil.copy2(legacy_path, runtime_path)


def _normalize_path_string(value, default=""):
    if value is None:
        return default
    if not isinstance(value, str):
        value = str(value)

    normalized = value.strip()
    if not normalized:
        return default

    if normalized in {DEFAULT_OUTPUT_PATH, os.path.normpath(DEFAULT_OUTPUT_PATH)}:
        return DEFAULT_OUTPUT_PATH

    return os.path.normpath(normalized)


def get_auto_batch_extract_workers():
    cpu_count = os.cpu_count() or 1
    return max(1, min(cpu_count, 8))


def resolve_batch_extract_workers(configured_workers):
    if not isinstance(configured_workers, int) or configured_workers <= 0:
        return get_auto_batch_extract_workers()
    return min(configured_workers, MAX_BATCH_EXTRACT_WORKERS)


def normalize_batch_extract_workers(value):
    if value in (None, "", DEFAULT_BATCH_EXTRACT_WORKERS):
        return DEFAULT_BATCH_EXTRACT_WORKERS

    parsed_value: int | None = None
    if isinstance(value, bool):
        parsed_value = None
    elif isinstance(value, int):
        parsed_value = value
    elif isinstance(value, float) and value.is_integer():
        parsed_value = int(value)
    elif isinstance(value, str):
        stripped_value = value.strip()
        if not stripped_value:
            return DEFAULT_BATCH_EXTRACT_WORKERS
        if stripped_value.isdigit():
            parsed_value = int(stripped_value)

    if parsed_value is None:
        log_error(f"{CONFIG_FILE} 中 batch_extract_workers 类型无效，已恢复自动模式")
        return DEFAULT_BATCH_EXTRACT_WORKERS

    if parsed_value < 0:
        log_error(f"{CONFIG_FILE} 中 batch_extract_workers 不能小于 0，已恢复自动模式")
        return DEFAULT_BATCH_EXTRACT_WORKERS

    if parsed_value > MAX_BATCH_EXTRACT_WORKERS:
        log_error(
            f"{CONFIG_FILE} 中 batch_extract_workers 超过上限 {MAX_BATCH_EXTRACT_WORKERS}，已截断为 {MAX_BATCH_EXTRACT_WORKERS}"
        )
        return MAX_BATCH_EXTRACT_WORKERS

    return parsed_value


def normalize_wallpaper_id(value):
    if value is None:
        return ""

    if isinstance(value, bool):
        return ""

    if isinstance(value, int):
        return str(value)

    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else ""

    text = str(value).strip()
    if not text:
        return ""

    if text.isdigit():
        return text

    return text


def normalize_wallpaper_title(value):
    if value is None:
        return ""

    text = str(value).strip()
    return "" if text == "None" else text


def normalize_wallpaper_type(value):
    text = normalize_wallpaper_title(value)
    return text.capitalize() if text else ""


def normalize_visibility(value):
    return normalize_wallpaper_title(value).lower()


def normalize_project_file(value):
    text = normalize_wallpaper_title(value)
    return _normalize_path_string(text) if text else ""


def normalize_preview_path(value):
    text = normalize_wallpaper_title(value)
    if not text:
        return ""
    return _normalize_path_string(text)


def normalize_tags(value):
    if value in (None, "", "None"):
        return []

    tags: list[Any]
    if isinstance(value, list):
        tags = value
    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            try:
                parsed = ast.literal_eval(value)
            except (ValueError, SyntaxError):
                log_error(f"解析标签失败，返回空列表: {value}")
                return []
        if not isinstance(parsed, list):
            log_error(f"解析标签失败，返回空列表: {value}")
            return []
        tags = parsed
    else:
        log_error(f"解析标签失败，返回空列表: {value}")
        return []

    normalized_tags = []
    for tag in tags:
        text = normalize_wallpaper_title(tag)
        if text:
            normalized_tags.append(text.capitalize())
    return normalized_tags


def serialize_tags(tags):
    return json.dumps(normalize_tags(tags), ensure_ascii=False)


def normalize_wallpaper_info(raw_record):
    if not isinstance(raw_record, dict):
        raise ValueError("壁纸记录必须是对象")

    return WallpaperInfo(
        preview=normalize_preview_path(raw_record.get("preview", "")),
        tags=normalize_tags(raw_record.get("tags", [])),
        title=normalize_wallpaper_title(raw_record.get("title", "")),
        type=normalize_wallpaper_type(raw_record.get("type", "")),
        visibility=normalize_visibility(raw_record.get("visibility", "")),
        file=normalize_project_file(raw_record.get("file", "")),
        id=normalize_wallpaper_id(raw_record.get("id", "")),
    )


def ensure_config_file():
    ensure_runtime_dir()
    migrate_legacy_runtime_files()
    if not os.path.exists(CONFIG_FILE):
        _write_json_file(CONFIG_FILE, DEFAULT_CONFIG)


def normalize_config_data(raw_config):
    if not isinstance(raw_config, dict):
        raise ValueError(f"{CONFIG_FILE} 顶层必须是 JSON 对象")

    unknown_keys = sorted(set(raw_config.keys()) - set(CONFIG_KEYS))
    if unknown_keys:
        log_error(f"{CONFIG_FILE} 包含未识别字段: {', '.join(unknown_keys)}")

    steam_path = raw_config.get("steam_path", "")
    if steam_path is None:
        steam_path = ""
    elif not isinstance(steam_path, str):
        log_error(f"{CONFIG_FILE} 中 steam_path 类型无效，已重置为空字符串")
        steam_path = ""
    else:
        steam_path = _normalize_path_string(steam_path)
        if steam_path and not steam_path.lower().endswith("steam.exe"):
            log_error(f"{CONFIG_FILE} 中 steam_path 不指向 steam.exe，已重置为空字符串")
            steam_path = ""

    output_path = raw_config.get("output_path", DEFAULT_OUTPUT_PATH)
    if output_path is None:
        output_path = DEFAULT_OUTPUT_PATH
    elif not isinstance(output_path, str):
        log_error(f"{CONFIG_FILE} 中 output_path 类型无效，已恢复默认值")
        output_path = DEFAULT_OUTPUT_PATH
    else:
        output_path = _normalize_path_string(output_path, DEFAULT_OUTPUT_PATH)

    batch_extract_workers = normalize_batch_extract_workers(
        raw_config.get("batch_extract_workers", DEFAULT_BATCH_EXTRACT_WORKERS)
    )

    return AppConfig(
        steam_path=steam_path,
        output_path=output_path,
        batch_extract_workers=batch_extract_workers,
    )


def load_config():
    ensure_config_file()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            raw_config = json.load(file)
    except json.JSONDecodeError as exc:
        log_error(f"{CONFIG_FILE} 文件格式错误: {exc}，已恢复默认配置")
        config = AppConfig()
        _write_json_file(CONFIG_FILE, config.to_dict())
        return config

    try:
        config = normalize_config_data(raw_config)
    except ValueError as exc:
        log_error(f"{exc}，已恢复默认配置")
        config = AppConfig()
        _write_json_file(CONFIG_FILE, config.to_dict())
        return config

    normalized = config.to_dict()
    if normalized != raw_config:
        _write_json_file(CONFIG_FILE, normalized)
        log_success(f"已规范化 {CONFIG_FILE} 配置内容")

    return config


def read_config_value(key):
    if key not in CONFIG_KEYS:
        raise KeyError(f"不支持的配置字段: {key}")

    config = load_config()
    value = getattr(config, key)
    if value:
        log_success(f"成功读取路径: {value}")
        return value

    return None


def write_config_value(key, value):
    if key not in CONFIG_KEYS:
        raise KeyError(f"不支持的配置字段: {key}")

    config = load_config()
    updated_config = config.to_dict()
    updated_config[key] = value
    normalized_config = normalize_config_data(updated_config)
    _write_json_file(CONFIG_FILE, normalized_config.to_dict())
    log_success(f"成功写入配置 {key}: {getattr(normalized_config, key)}")


def get_workshop_directory(steam_path):
    return os.path.join(os.path.dirname(steam_path), "steamapps", "workshop", "content", WORKSHOP_APP_ID)


def get_item_directory(steam_path, item_id):
    return os.path.join(get_workshop_directory(steam_path), str(item_id))


def get_scene_pkg_path(steam_path, item_id):
    return os.path.join(get_item_directory(steam_path, item_id), "scene.pkg")


def sanitize_wallpaper_title(title):
    return re.sub(r'[\\/*?:"<>|]', "", title)


def read_json_object(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"{file_path} 顶层必须是 JSON 对象")

    return data


def find_preview_file(folder_path, directory_entries):
    for filename in directory_entries:
        if filename.lower() in PREVIEW_FILENAMES:
            return os.path.join(folder_path, filename)
    return ""


def resolve_preview_path(folder_path, preview_value, directory_entries):
    preview_text = normalize_wallpaper_title(preview_value)
    normalized_preview = ""
    if preview_text:
        preview_path = preview_text
        if not os.path.isabs(preview_path):
            preview_path = os.path.join(folder_path, preview_path)
        normalized_preview = normalize_preview_path(preview_path)
        if normalized_preview and os.path.exists(normalized_preview):
            return normalized_preview

    fallback_preview = normalize_preview_path(find_preview_file(folder_path, directory_entries))
    return fallback_preview or normalized_preview


def collect_workshop_info(steam_path):
    if not steam_path:
        raise ValueError(f"{CONFIG_FILE} 中 steam_path 未找到或无效")

    directory = get_workshop_directory(steam_path)
    if not os.path.exists(directory):
        raise FileNotFoundError(f"目录 {directory} 不存在")

    extracted_info = []
    for foldername in os.listdir(directory):
        folder_path = os.path.join(directory, foldername)
        if not os.path.isdir(folder_path):
            continue

        try:
            directory_entries = sorted(os.listdir(folder_path))
        except OSError as exc:
            log_error(f"读取目录 {folder_path} 时发生错误: {exc}")
            continue

        project_data = {}
        json_candidates = sorted(
            (filename for filename in directory_entries if filename.lower().endswith(".json")),
            key=lambda filename: (filename.lower() != "project.json", filename.lower()),
        )
        for filename in json_candidates:
            file_path = os.path.join(folder_path, filename)
            try:
                project_data = read_json_object(file_path)
                break
            except (json.JSONDecodeError, OSError, ValueError) as exc:
                log_error(f"读取元数据文件 {file_path} 失败: {exc}")

        extracted_info.append(
            normalize_wallpaper_info(
                {
                    "id": normalize_wallpaper_id(foldername),
                    "preview": resolve_preview_path(folder_path, project_data.get("preview", ""), directory_entries),
                    "tags": project_data.get("tags", []),
                    "title": project_data.get("title", ""),
                    "type": project_data.get("type", ""),
                    "visibility": project_data.get("visibility", ""),
                    "file": project_data.get("file", ""),
                }
            )
        )

    return extracted_info


def extract_info_to_csv():
    steam_path = read_config_value("steam_path")
    extracted_info = collect_workshop_info(steam_path)
    ensure_runtime_dir()
    csv_file_path = INFO_CSV_FILE
    with open(csv_file_path, "w", newline="", encoding="utf-8") as csv_file:
        csv_writer = csv.DictWriter(csv_file, fieldnames=INFO_FIELDS)
        csv_writer.writeheader()
        csv_writer.writerows(record.to_csv_row() for record in extracted_info)
    return csv_file_path


def parse_tags(tags_str):
    return normalize_tags(tags_str)


def read_info_csv(file_path):
    try:
        df = pd.read_csv(file_path, keep_default_na=False)
        df = df.reindex(columns=INFO_FIELDS, fill_value="")
        df["preview"] = df["preview"].apply(normalize_preview_path)
        df["tags"] = df["tags"].apply(parse_tags)
        df["title"] = df["title"].apply(normalize_wallpaper_title)
        df["type"] = df["type"].apply(normalize_wallpaper_type)
        df["visibility"] = df["visibility"].apply(normalize_visibility)
        df["file"] = df["file"].apply(normalize_project_file)
        df["id"] = df["id"].apply(normalize_wallpaper_id)
        log_success(f"成功读取 CSV 文件: {file_path}")
        return df
    except FileNotFoundError:
        log_error(f"文件 {file_path} 未找到")
    except pd.errors.EmptyDataError:
        log_error(f"文件 {file_path} 为空")
    except pd.errors.ParserError:
        log_error(f"无法解析文件 {file_path}")
    except (OSError, ValueError) as exc:
        log_error(f"读取文件 {file_path} 时发生错误: {exc}")
    return None


def build_extract_command(options, item_id, title):
    scene_pkg_path = get_scene_pkg_path(options.steam_path, item_id)
    command = [REPKG_EXECUTABLE, "extract", scene_pkg_path]

    if options.not_convert_tex_to_image:
        command.append("--no-tex-convert")
    if options.copy_project_json_and_preview:
        command.append("-c")
    if options.overwrite_files:
        command.append("--overwrite")

    item_directory = get_item_directory(options.steam_path, item_id)
    output_path = options.output_path

    if options.output_mode == LOCAL_OUTPUT_MODE:
        local_output_path = output_path.replace(r"./", "")
        command.extend(["-o", os.path.join(item_directory, local_output_path)])
    elif options.output_mode == SHARED_OUTPUT_MODE:
        command.extend(["-o", output_path])
    elif options.output_mode == SEPARATE_OUTPUT_MODE:
        subdir_name = sanitize_wallpaper_title(title) if options.use_wallpaper_name_as_subdir else str(item_id)
        command.extend(["-o", os.path.join(output_path, subdir_name)])
    else:
        raise ValueError(f"无效的输出模式: {options.output_mode}")

    return command


def run_extract_command(command):
    return subprocess.run(command, shell=False, capture_output=True, text=True)
