import csv
import json
import os
import subprocess
import tempfile
import unittest
import weakref
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import app_services
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication
from PIL import Image
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
    extract_info_to_csv,
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
from repkg_gui.app_context import AppContext
from repkg_gui.app_metadata import REPKG_PROJECT_URL, REPKG_VERSION
from repkg_gui.image_utils import load_static_qimage
from repkg_gui.controllers.library_controller import LibraryController
from repkg_gui.controllers.settings_controller import (
    ABOUT_IMAGE_URL,
    CONFIG_DISPLAY_PATH,
    INFO_DISPLAY_PATH,
    SettingsController,
    build_help_sections,
    build_help_sections as build_secondary_help_sections,
    build_settings_summary as build_secondary_settings_summary,
    format_batch_extract_workers_display,
    get_batch_extract_workers_description,
    get_output_mode_description,
    load_about_metadata,
)
from repkg_gui.domain.entities import (
    ExtractionItemResult,
    ExtractionPlan,
    ExtractionRequest,
    ExtractionSummary,
    FilterState,
    SessionSettings,
    SkippedItem,
    WallpaperRecord,
)
from repkg_gui.domain.enums import FilterField, OutputMode
from repkg_gui.models.catalog_filter_proxy import CatalogFilterProxyModel
from repkg_gui.models.selection_model import (
    build_filter_status,
    build_loaded_status,
    build_selection_status,
    format_visibility as format_visibility_for_display,
    metadata_lines,
)
from repkg_gui.models.catalog_table_model import CatalogTableModel
from repkg_gui.services.catalog_service import CatalogService
from repkg_gui.services.extraction_service import ExtractionService, ExtractionValidationError
from repkg_gui.services.runtime_compat import RuntimeCompatService
from repkg_gui.services.steam_locator_service import SteamLocatorService
from repkg_gui.state.session_state import SessionState
from repkg_gui.ui.widgets.thumbnail_view import ThumbnailView
from repkg_gui.workers.extraction_worker import ExtractionWorker


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
            self.assertEqual(json.load(file), AppConfig().to_dict())

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
            self.assertEqual(json.load(file), AppConfig().to_dict())

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

    def test_write_config_values_persists_theme_configuration(self):
        app_services.write_config_values(
            {
                "theme_preset": "dark",
                "theme_background": "#101214",
                "theme_surface": "#1E2228",
                "theme_accent": "#7AA2FF",
                "theme_text": "#F7F9FC",
            }
        )

        config = load_config()
        self.assertEqual(config.theme_preset, "dark")
        self.assertEqual(config.theme_background, "#101214")
        self.assertEqual(config.theme_surface, "#1E2228")
        self.assertEqual(config.theme_accent, "#7AA2FF")
        self.assertEqual(config.theme_text, "#F7F9FC")

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

    def test_extract_info_to_csv_accepts_explicit_steam_path(self):
        steam_path, _ = self.create_workshop_item(
            "8899",
            project_data={
                "title": "Explicit Scan",
                "type": "scene",
                "tags": ["anime"],
                "file": "scene.json",
                "visibility": "private",
            },
        )

        csv_path = extract_info_to_csv(steam_path=steam_path)

        self.assertEqual(csv_path, app_services.INFO_CSV_FILE)
        self.assertTrue(os.path.exists(csv_path))
        dataframe = read_info_csv(csv_path)
        self.assertEqual(list(dataframe["id"]), ["8899"])

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
            build_filter_status(FilterField.TAGS, "Anime", 3, 10),
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
        state = SessionState(
            config=AppConfig(
                steam_path=r"C:\Program Files (x86)\Steam\steam.exe",
                output_path=r"D:\Exports",
            )
        )
        state.output_mode = SHARED_OUTPUT_MODE

        summary = build_secondary_settings_summary(state)

        self.assertIn(r"C:\Program Files (x86)\Steam\steam.exe", summary)
        self.assertIn(r"D:\Exports", summary)
        self.assertIn(SHARED_OUTPUT_MODE, summary)
        self.assertIn(CONFIG_DISPLAY_PATH, summary)
        self.assertIn("批量提取并发", summary)

    def test_build_help_sections_include_repkg_metadata_and_recent_features(self):
        sections = {section.title: section.lines for section in build_help_sections()}

        self.assertIn("设置页说明", sections)
        self.assertIn("文件位置", sections)
        self.assertTrue(any("刷新数据" in line for line in sections["常见操作"]))
        self.assertTrue(any(REPKG_VERSION in line for line in sections["文件位置"]))

    def test_format_visibility_for_display_returns_readable_labels(self):
        self.assertEqual(format_visibility_for_display("private"), "私有")
        self.assertEqual(format_visibility_for_display("PUBLIC"), "公开")
        self.assertEqual(format_visibility_for_display(""), "未标注")

    def test_build_wallpaper_metadata_summary_includes_needed_fields(self):
        summary = "\n".join(
            metadata_lines(
                WallpaperRecord(
                    id="1000",
                    type="Scene",
                    visibility="private",
                    file="scene.json",
                    preview_path=os.path.join(r"C:\Workshop", "preview.jpg"),
                )
            )
        )

        self.assertIn("类型：Scene", summary)
        self.assertIn("可见性：私有", summary)
        self.assertIn("项目文件：scene.json", summary)
        self.assertIn("预览文件：preview.jpg", summary)

    def test_repkg_metadata_constants_match_expected_values(self):
        self.assertEqual(REPKG_VERSION, "v0.4.0-alpha")
        self.assertEqual(REPKG_PROJECT_URL, "https://github.com/notscuffed/repkg")

    def test_summarize_extraction_results_includes_warning_counts(self):
        summary, status, has_warning = (
            ExtractionSummary(
                requested_count=4,
                succeeded=(
                    ExtractionItemResult(item_id="1001", title="A", success=True),
                    ExtractionItemResult(item_id="1002", title="B", success=True),
                ),
                skipped=(SkippedItem(item_id="1003", reason="缺少 scene.pkg"),),
                failed=(
                    ExtractionItemResult(item_id="1004", title="C", success=False, error="未找到对应的壁纸信息"),
                ),
            ).to_display_messages()
        )

        self.assertEqual(
            summary,
            "成功提取 2 项\n缺少 scene.pkg: 1003\n执行失败: 1004(未找到对应的壁纸信息)",
        )
        self.assertEqual(status, "提取完成：成功 2 项，缺少资源 1 项，失败 1 项")
        self.assertTrue(has_warning)

    def test_secondary_settings_summary_mentions_runtime_contract(self):
        state = SessionState(
            config=AppConfig(
                steam_path=r"C:\Program Files (x86)\Steam\steam.exe",
                output_path=r"D:\Exports",
                batch_extract_workers=0,
            )
        )
        state.output_mode = SHARED_OUTPUT_MODE
        state.copy_project_json_and_preview = True

        summary = build_secondary_settings_summary(state)

        self.assertIn(CONFIG_DISPLAY_PATH, summary)
        self.assertIn(INFO_DISPLAY_PATH, summary)
        self.assertIn("持久化设置", summary)
        self.assertIn("复制 project.json / 预览：是", summary)
        self.assertIn("主题预设", summary)

    def test_secondary_settings_worker_helpers_report_auto_and_manual_modes(self):
        self.assertIn("自动", format_batch_extract_workers_display(0))
        self.assertIn("线程", format_batch_extract_workers_display(4))
        self.assertIn("CPU 核心数", get_batch_extract_workers_description(0))
        self.assertIn("填 0 可切回自动模式", get_batch_extract_workers_description(3))

    def test_secondary_help_sections_preserve_legacy_structure(self):
        sections = {section.title: section.lines for section in build_secondary_help_sections()}

        self.assertIn("设置页说明", sections)
        self.assertIn("文件位置", sections)
        self.assertTrue(any("批量提取并发数填 0" in line for line in sections["设置页说明"]))

    def test_secondary_about_metadata_exposes_links_and_image(self):
        metadata = load_about_metadata()

        self.assertEqual(metadata.repkg_project_url, REPKG_PROJECT_URL)
        self.assertEqual(metadata.support_image_url, ABOUT_IMAGE_URL)
        self.assertTrue(metadata.support_image_path.endswith("nekomusume.png"))


class ServiceLayerTests(AppServicesTests):
    def setUp(self):
        super().setUp()
        self.runtime = RuntimeCompatService()
        self.catalog_service = CatalogService(runtime=self.runtime)
        self.extraction_service = ExtractionService(runtime=self.runtime)

    def test_runtime_compat_creates_session_settings_from_config(self):
        steam_path, _ = self.create_workshop_item("1000")
        config = AppConfig(
            steam_path=steam_path,
            output_path=r"D:\Exports",
            batch_extract_workers=7,
        )

        settings = self.runtime.session_settings_from_config(config)
        runtime_options = self.runtime.build_extraction_options(settings)

        self.assertEqual(settings.output_mode, OutputMode.SEPARATE)
        self.assertEqual(runtime_options.output_mode, SEPARATE_OUTPUT_MODE)
        self.assertEqual(runtime_options.output_path, r"D:\Exports")

    def test_catalog_service_scan_catalog_returns_typed_snapshot(self):
        steam_path, workshop_dir = self.create_workshop_item(
            "12345",
            project_data={
                "title": "Service Title",
                "type": "scene",
                "tags": ["anime", "scenery"],
                "preview": "preview.jpg",
                "file": "scene.json",
                "visibility": "private",
            },
        )

        snapshot = self.catalog_service.scan_catalog(steam_path)

        self.assertEqual(snapshot.steam_path, steam_path)
        self.assertEqual(snapshot.csv_path, app_services.INFO_CSV_FILE)
        self.assertEqual(snapshot.total_count, 1)
        self.assertEqual(snapshot.records[0].title, "Service Title")
        self.assertEqual(snapshot.records[0].tags, ("Anime", "Scenery"))
        self.assertEqual(snapshot.records[0].preview_path, os.path.join(workshop_dir, "preview.jpg"))

    def test_steam_locator_service_finds_common_install_path_without_drive_scan(self):
        common_install_dir = os.path.join(self.temp_dir.name, "SteamCommon")
        os.makedirs(common_install_dir, exist_ok=True)
        expected_path = os.path.join(common_install_dir, "steam.exe")
        with open(expected_path, "w", encoding="utf-8") as file:
            file.write("")

        service = SteamLocatorService(common_paths=(common_install_dir,))

        self.assertEqual(service.find_steam_path(include_all_drives=False), expected_path)

    def test_extraction_service_prepare_requests_tracks_valid_missing_and_unknown_items(self):
        steam_path, valid_dir = self.create_workshop_item(
            "12345",
            project_data={"title": "Ready", "type": "scene", "file": "scene.json"},
        )
        _, missing_scene_dir = self.create_workshop_item(
            "54321",
            project_data={"title": "Missing Scene", "type": "scene", "file": "scene.json"},
        )
        with open(os.path.join(valid_dir, "scene.pkg"), "wb") as file:
            file.write(b"pkg")

        records = (
            WallpaperRecord(id="12345", title="Ready"),
            WallpaperRecord(id="54321", title="Missing Scene"),
        )

        plan = self.extraction_service.prepare_requests(records, ["12345", "54321", "99999"], steam_path)

        self.assertEqual([request.item_id for request in plan.requests], ["12345"])
        self.assertEqual(
            [(item.item_id, item.reason) for item in plan.skipped],
            [("54321", "缺少 scene.pkg"), ("99999", "未找到对应的壁纸信息")],
        )
        self.assertFalse(os.path.exists(os.path.join(missing_scene_dir, "scene.pkg")))

    def test_extraction_service_execute_requests_summarizes_success_and_failures(self):
        steam_path, first_dir = self.create_workshop_item(
            "12345",
            project_data={"title": "First", "type": "scene", "file": "scene.json"},
        )
        _, second_dir = self.create_workshop_item(
            "54321",
            project_data={"title": "Second", "type": "scene", "file": "scene.json"},
        )
        with open(os.path.join(first_dir, "scene.pkg"), "wb") as file:
            file.write(b"pkg")
        with open(os.path.join(second_dir, "scene.pkg"), "wb") as file:
            file.write(b"pkg")

        plan = self.extraction_service.prepare_requests(
            (
                WallpaperRecord(id="12345", title="First"),
                WallpaperRecord(id="54321", title="Second"),
            ),
            ["12345", "54321"],
            steam_path,
        )
        settings = SessionSettings(
            steam_path=steam_path,
            output_path=os.path.join(self.temp_dir.name, "exports"),
            output_mode=OutputMode.SEPARATE,
            batch_extract_workers=8,
        )

        def fake_run(command):
            item_id = os.path.basename(os.path.dirname(command[2]))
            if item_id == "12345":
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
            return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")

        with patch.object(
            RuntimeCompatService,
            "run_extract_command",
            autospec=True,
            side_effect=lambda _self, command: fake_run(command),
        ):
            summary = self.extraction_service.execute_requests(plan, settings)

        self.assertEqual(summary.requested_count, 2)
        self.assertEqual(summary.success_ids, ("12345",))
        self.assertEqual(summary.failed_ids, ("54321",))
        self.assertEqual(summary.failed[0].error, "boom")
        self.assertEqual(summary.effective_workers, 2)
        self.assertFalse(summary.skipped)

    def test_extraction_summary_formats_missing_scene_and_failures_like_legacy_ui(self):
        summary = ExtractionSummary(
            requested_count=4,
            succeeded=(ExtractionItemResult(item_id="1001", title="A", success=True),),
            failed=(ExtractionItemResult(item_id="1004", title="D", success=False, error="boom"),),
            skipped=(
                SkippedItem(item_id="1002", reason="缺少 scene.pkg"),
                SkippedItem(item_id="1003", reason="未找到对应的壁纸信息"),
            ),
            effective_workers=2,
        )

        summary_message, status_message, has_warning = summary.to_display_messages()

        self.assertEqual(
            summary_message,
            "成功提取 1 项\n缺少 scene.pkg: 1002\n执行失败: 1003(未找到对应的壁纸信息), 1004(boom)",
        )
        self.assertEqual(status_message, "提取完成：成功 1 项，缺少资源 1 项，失败 2 项")
        self.assertTrue(has_warning)

    def test_extraction_service_resolve_effective_workers_returns_zero_without_requests(self):
        settings = SessionSettings(batch_extract_workers=8)

        self.assertEqual(self.extraction_service.resolve_effective_workers(ExtractionPlan(), settings), 0)


class PySideArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.qt_app = QApplication.instance() or QApplication([])

    def _build_context(self, config: AppConfig | None = None) -> AppContext:
        return AppContext.from_config(config or AppConfig())

    def test_app_context_set_catalog_records_prunes_missing_selection_and_focus(self):
        context = self._build_context()
        context.state.selected_wallpaper_ids = {"1001", "missing"}
        context.state.focused_wallpaper_id = "missing"

        context.set_catalog_records(
            (
                WallpaperRecord(id="1001", title="Kept"),
                WallpaperRecord(id="1002", title="Other"),
            )
        )

        self.assertEqual(context.state.catalog_count, 2)
        self.assertEqual(context.state.selected_wallpaper_ids, {"1001"})
        self.assertIsNone(context.state.focused_wallpaper_id)

    def test_settings_controller_supports_weak_references_for_qt_signal_bindings(self):
        controller = SettingsController(self._build_context())

        controller_ref = weakref.ref(controller)

        self.assertIs(controller_ref(), controller)

    def test_library_controller_select_all_visible_updates_context_selection(self):
        context = self._build_context()
        controller = LibraryController(context)
        controller.table_model.set_records(
            (
                WallpaperRecord(id="1001", title="Alpha"),
                WallpaperRecord(id="1002", title="Beta"),
            )
        )

        controller.select_all_visible()

        self.assertEqual(controller.visible_count(), 2)
        self.assertEqual(context.state.selected_wallpaper_ids, {"1001", "1002"})
        self.assertEqual(context.state.focused_wallpaper_id, "1001")
        self.assertEqual(context.state.status_message, "已选择 2 项，当前列表共 2 项。")

    def test_catalog_filter_proxy_model_filters_tags_and_sorts_numeric_ids(self):
        model = CatalogTableModel(
            (
                WallpaperRecord(id="10", title="Alpha", tags=("Anime",), type="Scene"),
                WallpaperRecord(id="2", title="City Lights", tags=("City", "SciFi"), type="Video"),
                WallpaperRecord(id="1", title="Forest", tags=("City",), type="Scene"),
            )
        )
        proxy = CatalogFilterProxyModel()
        proxy.setSourceModel(model)

        proxy.set_filter_state(FilterState(field=FilterField.TAGS, value="city"))
        self.assertEqual(proxy.visible_item_ids(), ("2", "1"))

        proxy.set_filter_state(FilterState(field=FilterField.TITLE, value=""))
        proxy.sort(CatalogTableModel.COLUMN_ID)
        self.qt_app.processEvents()
        self.assertEqual(proxy.visible_item_ids(), ("1", "2", "10"))

    def test_load_static_qimage_supports_gif_first_frame(self):
        gif_path = os.path.join(tempfile.gettempdir(), "repkg_gui_test_preview.gif")
        first_frame = Image.new("RGBA", (24, 24), color=(0, 0, 0, 255))
        second_frame = Image.new("RGBA", (24, 24), color=(255, 0, 0, 255))
        first_frame.save(gif_path, save_all=True, append_images=[second_frame], duration=100, loop=0)
        self.addCleanup(lambda: os.path.exists(gif_path) and os.remove(gif_path))

        image = load_static_qimage(gif_path)

        self.assertFalse(image.isNull())
        self.assertEqual((image.width(), image.height()), (24, 24))
        self.assertEqual(image.pixelColor(image.width() // 2, image.height() // 2).red(), 255)

    def test_thumbnail_view_reads_first_frame_from_gif_previews(self):
        gif_path = os.path.join(tempfile.gettempdir(), "repkg_gui_test_thumbnail_preview.gif")
        first_frame = Image.new("RGBA", (32, 32), color=(0, 0, 0, 255))
        second_frame = Image.new("RGBA", (32, 32), color=(255, 0, 0, 255))
        first_frame.save(gif_path, save_all=True, append_images=[second_frame], duration=100, loop=0)
        self.addCleanup(lambda: os.path.exists(gif_path) and os.remove(gif_path))

        model = CatalogTableModel((WallpaperRecord(id="1001", title="Gif", preview_path=gif_path),))
        view = ThumbnailView()
        view.setModel(model)

        pixmap = view.thumbnail_for_index(model.index(0, CatalogTableModel.COLUMN_TITLE), QSize(96, 72))

        self.assertFalse(pixmap.isNull())
        self.assertEqual(pixmap.toImage().pixelColor(pixmap.width() // 2, pixmap.height() // 2).red(), 255)

    def test_extraction_worker_emits_started_progress_and_finished(self):
        plan = ExtractionPlan(
            requests=(
                ExtractionRequest(
                    item_id="1001",
                    title="Ready",
                    scene_pkg_path=r"C:\Workshop\1001\scene.pkg",
                    item_directory=r"C:\Workshop\1001",
                ),
            ),
            skipped=(SkippedItem(item_id="1002", reason="缺少 scene.pkg"),),
        )
        summary = ExtractionSummary(
            requested_count=2,
            succeeded=(ExtractionItemResult(item_id="1001", title="Ready", success=True),),
            skipped=plan.skipped,
            effective_workers=1,
        )

        class StubExtractionService:
            def validate_environment(self, settings):
                self.validated_settings = settings

            def prepare_requests(self, records, item_ids, steam_path):
                self.records = tuple(records)
                self.item_ids = tuple(item_ids)
                self.steam_path = steam_path
                return plan

            def resolve_effective_workers(self, resolved_plan, settings):
                return 1

            def execute_requests(self, resolved_plan, settings, on_result=None):
                if on_result is not None:
                    on_result(summary.succeeded[0])
                return summary

        service = StubExtractionService()
        worker = ExtractionWorker(
            service=service,
            records=(WallpaperRecord(id="1001", title="Ready"),),
            item_ids=("1001", "1002"),
            settings=SessionSettings(steam_path=r"C:\Program Files (x86)\Steam\steam.exe"),
        )
        started_events = []
        progress_events = []
        finished_events = []
        failed_messages = []
        worker.started.connect(started_events.append)
        worker.progress.connect(progress_events.append)
        worker.finished.connect(finished_events.append)
        worker.failed.connect(failed_messages.append)

        worker.run()

        self.assertFalse(failed_messages)
        self.assertEqual(started_events[0].requested_count, 2)
        self.assertEqual(started_events[0].skipped_count, 1)
        self.assertEqual([event.completed for event in progress_events], [1, 2])
        self.assertIn("预先跳过 1 项", progress_events[0].message)
        self.assertEqual(finished_events[0].summary.success_ids, ("1001",))

    def test_extraction_worker_emits_failed_when_validation_fails(self):
        class FailingExtractionService:
            def validate_environment(self, settings):
                raise ExtractionValidationError("steam_path 未找到或无效")

        worker = ExtractionWorker(
            service=FailingExtractionService(),
            records=(),
            item_ids=(),
            settings=SessionSettings(),
        )
        failed_messages = []
        worker.failed.connect(failed_messages.append)

        worker.run()

        self.assertEqual(failed_messages, ["steam_path 未找到或无效"])


if __name__ == "__main__":
    unittest.main()
