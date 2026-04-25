import csv
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import app_services
from app_services import (
    DEFAULT_BATCH_EXTRACT_WORKERS,
    DEFAULT_OUTPUT_PATH,
    LOCAL_OUTPUT_MODE,
    MAX_BATCH_EXTRACT_WORKERS,
    REPKG_EXECUTABLE,
    SEPARATE_OUTPUT_MODE,
    SHARED_OUTPUT_MODE,
    AppConfig,
    ExtractionOptions,
    WallpaperInfo,
    build_extract_command,
    collect_workshop_info,
    get_auto_batch_extract_workers,
    get_item_directory,
    get_scene_pkg_path,
    load_config,
    normalize_batch_extract_workers,
    parse_tags,
    read_info_csv,
    resolve_batch_extract_workers,
    serialize_tags,
    sanitize_wallpaper_title,
    write_config_value,
)
from main import (
    CONFIG_DISPLAY_PATH,
    REPKG_PROJECT_URL,
    REPKG_VERSION,
    build_help_sections,
    build_filter_status,
    build_loaded_status,
    build_selection_status,
    build_settings_summary,
    build_wallpaper_metadata_summary,
    format_visibility_for_display,
    get_output_mode_description,
    summarize_extraction_results,
)


class AppServicesTests(unittest.TestCase):
    def setUp(self):
        self.options = ExtractionOptions(
            steam_path=r"C:\Program Files (x86)\Steam\steam.exe",
            output_path=r"C:\Exports",
            output_mode=SEPARATE_OUTPUT_MODE,
            not_convert_tex_to_image=True,
            use_wallpaper_name_as_subdir=True,
            copy_project_json_and_preview=True,
            overwrite_files=True,
        )
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_runtime_dir = os.path.join(self.temp_dir.name, "runtime")
        self.temp_legacy_dir = os.path.join(self.temp_dir.name, "legacy")
        os.makedirs(self.temp_runtime_dir, exist_ok=True)
        os.makedirs(self.temp_legacy_dir, exist_ok=True)
        self.original_runtime_dir = app_services.RUNTIME_DIR
        self.original_config_file = app_services.CONFIG_FILE
        self.original_log_file = app_services.LOG_FILE
        self.original_error_log_file = app_services.ERROR_LOG_FILE
        self.original_info_csv_file = app_services.INFO_CSV_FILE
        self.original_legacy_config_file = app_services.LEGACY_CONFIG_FILE
        self.original_legacy_log_file = app_services.LEGACY_LOG_FILE
        self.original_legacy_error_log_file = app_services.LEGACY_ERROR_LOG_FILE
        self.original_legacy_info_csv_file = app_services.LEGACY_INFO_CSV_FILE
        app_services.RUNTIME_DIR = self.temp_runtime_dir
        app_services.CONFIG_FILE = os.path.join(self.temp_runtime_dir, "config.json")
        app_services.LOG_FILE = os.path.join(self.temp_runtime_dir, "logs.txt")
        app_services.ERROR_LOG_FILE = os.path.join(self.temp_runtime_dir, "errors.txt")
        app_services.INFO_CSV_FILE = os.path.join(self.temp_runtime_dir, "info.csv")
        app_services.LEGACY_CONFIG_FILE = os.path.join(self.temp_legacy_dir, "config.json")
        app_services.LEGACY_LOG_FILE = os.path.join(self.temp_legacy_dir, "logs.txt")
        app_services.LEGACY_ERROR_LOG_FILE = os.path.join(self.temp_legacy_dir, "errors.txt")
        app_services.LEGACY_INFO_CSV_FILE = os.path.join(self.temp_legacy_dir, "info.csv")

    def tearDown(self):
        app_services.RUNTIME_DIR = self.original_runtime_dir
        app_services.CONFIG_FILE = self.original_config_file
        app_services.LOG_FILE = self.original_log_file
        app_services.ERROR_LOG_FILE = self.original_error_log_file
        app_services.INFO_CSV_FILE = self.original_info_csv_file
        app_services.LEGACY_CONFIG_FILE = self.original_legacy_config_file
        app_services.LEGACY_LOG_FILE = self.original_legacy_log_file
        app_services.LEGACY_ERROR_LOG_FILE = self.original_legacy_error_log_file
        app_services.LEGACY_INFO_CSV_FILE = self.original_legacy_info_csv_file
        self.temp_dir.cleanup()

    def create_workshop_item(
        self,
        item_id,
        project_data=None,
        fallback_json_name=None,
        fallback_json_data=None,
        preview_name="preview.jpg",
    ):
        steam_dir = os.path.join(self.temp_dir.name, "Steam")
        workshop_dir = os.path.join(
            steam_dir,
            "steamapps",
            "workshop",
            "content",
            app_services.WORKSHOP_APP_ID,
            str(item_id),
        )
        os.makedirs(workshop_dir, exist_ok=True)

        steam_path = os.path.join(steam_dir, "steam.exe")
        with open(steam_path, "w", encoding="utf-8") as file:
            file.write("")

        if preview_name:
            with open(os.path.join(workshop_dir, preview_name), "wb") as file:
                file.write(b"preview")

        if project_data is not None:
            with open(os.path.join(workshop_dir, "project.json"), "w", encoding="utf-8") as file:
                json.dump(project_data, file, ensure_ascii=False, indent=2)

        if fallback_json_name and fallback_json_data is not None:
            with open(os.path.join(workshop_dir, fallback_json_name), "w", encoding="utf-8") as file:
                json.dump(fallback_json_data, file, ensure_ascii=False, indent=2)

        return steam_path, workshop_dir

    def test_parse_tags_returns_list(self):
        self.assertEqual(parse_tags("['Anime', 'Scenery']"), ["Anime", "Scenery"])

    def test_parse_tags_supports_json_serialization(self):
        self.assertEqual(parse_tags('["Anime", "Scenery"]'), ["Anime", "Scenery"])

    def test_parse_tags_returns_empty_list_for_invalid_input(self):
        self.assertEqual(parse_tags("not-a-list"), [])

    def test_serialize_tags_writes_json_string(self):
        self.assertEqual(serialize_tags(["Anime", "Scenery"]), '["Anime", "Scenery"]')

    def test_sanitize_wallpaper_title_removes_windows_invalid_characters(self):
        self.assertEqual(sanitize_wallpaper_title('A:/B*?"<>|Wallpaper'), "ABWallpaper")

    def test_resource_root_defaults_to_source_directory_when_not_frozen(self):
        expected_root = os.path.dirname(os.path.abspath(app_services.__file__))

        with patch.object(app_services.sys, "frozen", False, create=True):
            self.assertEqual(app_services._get_resource_root(), expected_root)
            self.assertEqual(app_services._get_app_root(), expected_root)

    def test_resource_root_and_app_root_split_when_running_from_pyinstaller(self):
        with (
            patch.object(app_services.sys, "frozen", True, create=True),
            patch.object(app_services.sys, "_MEIPASS", r"C:\Bundle\_internal", create=True),
            patch.object(app_services.sys, "executable", r"C:\Bundle\RePKG_GUI.exe"),
        ):
            self.assertEqual(app_services._get_resource_root(), r"C:\Bundle\_internal")
            self.assertEqual(app_services._get_app_root(), r"C:\Bundle")

    def test_build_extract_command_for_separate_output_mode_uses_title_subdir(self):
        command = build_extract_command(self.options, 12345, "My:Wallpaper")

        self.assertEqual(command[:3], [REPKG_EXECUTABLE, "extract", get_scene_pkg_path(self.options.steam_path, 12345)])
        self.assertIn("--no-tex-convert", command)
        self.assertIn("-c", command)
        self.assertIn("--overwrite", command)
        self.assertEqual(command[-2:], ["-o", os.path.join(r"C:\Exports", "MyWallpaper")])

    def test_build_extract_command_for_local_output_mode_uses_item_output_folder(self):
        options = ExtractionOptions(
            steam_path=self.options.steam_path,
            output_path="./output",
            output_mode=LOCAL_OUTPUT_MODE,
        )

        command = build_extract_command(options, 54321, "Ignored")

        self.assertEqual(
            command[-2:],
            ["-o", os.path.join(get_item_directory(options.steam_path, 54321), "output")],
        )

    def test_build_extract_command_for_shared_output_mode_uses_shared_folder(self):
        options = ExtractionOptions(
            steam_path=self.options.steam_path,
            output_path=r"D:\SharedOutput",
            output_mode=SHARED_OUTPUT_MODE,
        )

        command = build_extract_command(options, 777, "Ignored")

        self.assertEqual(command[-2:], ["-o", r"D:\SharedOutput"])

    def test_load_config_creates_default_schema(self):
        config = load_config()

        self.assertEqual(config, AppConfig())
        with open(app_services.CONFIG_FILE, "r", encoding="utf-8") as file:
            self.assertEqual(
                json.load(file),
                {
                    "steam_path": "",
                    "output_path": DEFAULT_OUTPUT_PATH,
                    "batch_extract_workers": DEFAULT_BATCH_EXTRACT_WORKERS,
                },
            )

    def test_load_config_repairs_invalid_types_and_unknown_keys(self):
        with open(app_services.CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "steam_path": 123,
                    "output_path": "",
                    "unexpected": True,
                },
                file,
                indent=4,
            )

        config = load_config()

        self.assertEqual(
            config,
            AppConfig(
                steam_path="",
                output_path=DEFAULT_OUTPUT_PATH,
                batch_extract_workers=DEFAULT_BATCH_EXTRACT_WORKERS,
            ),
        )
        with open(app_services.CONFIG_FILE, "r", encoding="utf-8") as file:
            self.assertEqual(
                json.load(file),
                {
                    "steam_path": "",
                    "output_path": DEFAULT_OUTPUT_PATH,
                    "batch_extract_workers": DEFAULT_BATCH_EXTRACT_WORKERS,
                },
            )

    def test_write_config_value_normalizes_invalid_steam_path(self):
        write_config_value("steam_path", r"C:\Program Files\Steam\steam.txt")

        config = load_config()
        self.assertEqual(config.steam_path, "")

    def test_write_config_value_persists_valid_output_path(self):
        write_config_value("output_path", r"D:\Exports")

        config = load_config()
        self.assertEqual(config.output_path, r"D:\Exports")

    def test_write_config_value_persists_batch_extract_workers(self):
        write_config_value("batch_extract_workers", 6)

        config = load_config()
        self.assertEqual(config.batch_extract_workers, 6)

    def test_load_config_migrates_legacy_runtime_files(self):
        with open(app_services.LEGACY_CONFIG_FILE, "w", encoding="utf-8") as file:
            json.dump({"steam_path": "", "output_path": r"D:\LegacyOutput"}, file, indent=4)

        config = load_config()

        self.assertEqual(config.output_path, r"D:\LegacyOutput")
        self.assertTrue(os.path.exists(app_services.CONFIG_FILE))

    def test_wallpaper_info_serializes_to_csv_row(self):
        wallpaper = WallpaperInfo(
            preview=r"C:\Workshop\preview.jpg",
            tags=["Anime", "Scenery"],
            title="Sample",
            type="Scene",
            visibility="private",
            file="scene.json",
            id="12345",
        )

        self.assertEqual(
            wallpaper.to_csv_row(),
            {
                "preview": r"C:\Workshop\preview.jpg",
                "tags": '["Anime", "Scenery"]',
                "title": "Sample",
                "type": "Scene",
                "visibility": "private",
                "file": "scene.json",
                "id": "12345",
            },
        )

    def test_collect_workshop_info_prefers_project_json_and_keeps_needed_fields(self):
        steam_path, workshop_dir = self.create_workshop_item(
            "12345",
            project_data={
                "title": "Project Title",
                "type": "scene",
                "tags": ["anime"],
                "preview": "preview.jpg",
                "file": "scene.json",
                "visibility": "private",
            },
            fallback_json_name="scene.json",
            fallback_json_data={"title": "Fallback Title", "type": "video"},
        )

        records = collect_workshop_info(steam_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].title, "Project Title")
        self.assertEqual(records[0].type, "Scene")
        self.assertEqual(records[0].tags, ["Anime"])
        self.assertEqual(records[0].file, "scene.json")
        self.assertEqual(records[0].visibility, "private")
        self.assertEqual(records[0].preview, os.path.join(workshop_dir, "preview.jpg"))

    def test_collect_workshop_info_falls_back_to_other_json_when_project_json_missing(self):
        steam_path, workshop_dir = self.create_workshop_item(
            "54321",
            project_data=None,
            fallback_json_name="scene.json",
            fallback_json_data={
                "title": "Fallback Title",
                "type": "scene",
                "tags": ["scenery"],
                "file": "scene.json",
                "visibility": "public",
            },
        )

        records = collect_workshop_info(steam_path)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].title, "Fallback Title")
        self.assertEqual(records[0].file, "scene.json")
        self.assertEqual(records[0].visibility, "public")
        self.assertEqual(records[0].preview, os.path.join(workshop_dir, "preview.jpg"))

    def test_read_info_csv_normalizes_types(self):
        csv_path = os.path.join(self.temp_dir.name, "info.csv")
        with open(csv_path, "w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["preview", "tags", "title", "type", "visibility", "file", "id"])
            writer.writeheader()
            writer.writerow(
                {
                    "preview": "C:/Workshop/preview.jpg",
                    "tags": '["anime", "scenery"]',
                    "title": "Wallpaper A",
                    "type": "scene",
                    "visibility": "private",
                    "file": "scene.json",
                    "id": "1001",
                }
            )
            writer.writerow(
                {
                    "preview": "",
                    "tags": "['legacy']",
                    "title": "Wallpaper B",
                    "type": "video",
                    "visibility": "public",
                    "file": "video.json",
                    "id": 1002,
                }
            )

        df = read_info_csv(csv_path)

        self.assertEqual(df.iloc[0]["preview"], os.path.normpath(r"C:\Workshop\preview.jpg"))
        self.assertEqual(df.iloc[0]["tags"], ["Anime", "Scenery"])
        self.assertEqual(df.iloc[0]["type"], "Scene")
        self.assertEqual(df.iloc[0]["visibility"], "private")
        self.assertEqual(df.iloc[0]["file"], "scene.json")
        self.assertEqual(df.iloc[0]["id"], "1001")
        self.assertEqual(df.iloc[1]["preview"], "")
        self.assertEqual(df.iloc[1]["tags"], ["Legacy"])
        self.assertEqual(df.iloc[1]["type"], "Video")
        self.assertEqual(df.iloc[1]["visibility"], "public")
        self.assertEqual(df.iloc[1]["file"], "video.json")
        self.assertEqual(df.iloc[1]["id"], "1002")

    def test_read_info_csv_returns_none_when_read_raises_os_error(self):
        with patch("app_services.pd.read_csv", side_effect=PermissionError("denied")):
            self.assertIsNone(read_info_csv(r"C:\broken.csv"))

    def test_normalize_batch_extract_workers_supports_auto_and_clamp(self):
        self.assertEqual(normalize_batch_extract_workers(""), DEFAULT_BATCH_EXTRACT_WORKERS)
        self.assertEqual(normalize_batch_extract_workers("4"), 4)
        self.assertEqual(normalize_batch_extract_workers(MAX_BATCH_EXTRACT_WORKERS + 10), MAX_BATCH_EXTRACT_WORKERS)

    def test_resolve_batch_extract_workers_uses_auto_when_configured_zero(self):
        self.assertEqual(resolve_batch_extract_workers(0), get_auto_batch_extract_workers())
        self.assertEqual(resolve_batch_extract_workers(5), 5)

    def test_build_loaded_status_supports_refresh_message(self):
        self.assertEqual(build_loaded_status(12), "已加载 12 项壁纸数据。")
        self.assertEqual(build_loaded_status(12, refreshed=True), "刷新完成，已加载 12 项壁纸数据。")

    def test_build_filter_status_reports_match_counts(self):
        self.assertEqual(
            build_filter_status("标签", "Anime", 3, 10),
            "已按标签筛选“Anime”，匹配 3/10 项。",
        )

    def test_build_selection_status_reports_selected_and_unselected_states(self):
        self.assertEqual(build_selection_status(0, 8), "当前未选择项目，当前列表共 8 项。")
        self.assertEqual(build_selection_status(2, 8), "已选择 2 项，当前列表共 8 项。")

    def test_get_output_mode_description_returns_expected_text(self):
        self.assertIn("output 文件夹", get_output_mode_description(LOCAL_OUTPUT_MODE))
        self.assertIn("同一个目录", get_output_mode_description(SHARED_OUTPUT_MODE))
        self.assertIn("分开建文件夹", get_output_mode_description(SEPARATE_OUTPUT_MODE))

    def test_build_settings_summary_includes_core_paths(self):
        summary = build_settings_summary(r"C:\Program Files (x86)\Steam\steam.exe", r"D:\Exports", SHARED_OUTPUT_MODE)

        self.assertIn(r"C:\Program Files (x86)\Steam\steam.exe", summary)
        self.assertIn(r"D:\Exports", summary)
        self.assertIn(SHARED_OUTPUT_MODE, summary)
        self.assertIn(CONFIG_DISPLAY_PATH, summary)
        self.assertIn("批量提取并发", summary)

    def test_build_help_sections_include_repkg_metadata_and_recent_features(self):
        sections = dict(build_help_sections())

        self.assertIn("设置页说明", sections)
        self.assertIn("文件位置", sections)
        self.assertTrue(any("刷新数据" in line for line in sections["常见操作"]))
        self.assertTrue(any(REPKG_VERSION in line for line in sections["文件位置"]))

    def test_format_visibility_for_display_returns_readable_labels(self):
        self.assertEqual(format_visibility_for_display("private"), "私有")
        self.assertEqual(format_visibility_for_display("PUBLIC"), "公开")
        self.assertEqual(format_visibility_for_display(""), "未标注")

    def test_build_wallpaper_metadata_summary_includes_needed_fields(self):
        summary = build_wallpaper_metadata_summary(
            {
                "type": "scene",
                "visibility": "private",
                "file": "scene.json",
                "preview": os.path.join(r"C:\Workshop", "preview.jpg"),
            }
        )

        self.assertIn("类型：Scene", summary)
        self.assertIn("可见性：私有", summary)
        self.assertIn("项目文件：scene.json", summary)
        self.assertIn("预览文件：preview.jpg", summary)

    def test_repkg_metadata_constants_match_expected_values(self):
        self.assertEqual(REPKG_VERSION, "v0.4.0-alpha")
        self.assertEqual(REPKG_PROJECT_URL, "https://github.com/notscuffed/repkg")

    def test_summarize_extraction_results_includes_warning_counts(self):
        summary, status, has_warning = summarize_extraction_results(
            ["1001", "1002"],
            ["1003"],
            [("1004", "未找到对应的壁纸信息")],
        )

        self.assertEqual(
            summary,
            "成功提取 2 项\n缺少 scene.pkg: 1003\n执行失败: 1004(未找到对应的壁纸信息)",
        )
        self.assertEqual(status, "提取完成：成功 2 项，缺少资源 1 项，失败 1 项")
        self.assertTrue(has_warning)


if __name__ == "__main__":
    unittest.main()
