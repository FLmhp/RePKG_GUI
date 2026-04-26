from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import app_services
from repkg_gui.domain.entities import SessionSettings
from repkg_gui.domain.enums import OutputMode

RUNTIME_OUTPUT_MODE_BY_DOMAIN = {
    OutputMode.LOCAL: app_services.LOCAL_OUTPUT_MODE,
    OutputMode.SHARED: app_services.SHARED_OUTPUT_MODE,
    OutputMode.SEPARATE: app_services.SEPARATE_OUTPUT_MODE,
}
DOMAIN_OUTPUT_MODE_BY_RUNTIME = {value: key for key, value in RUNTIME_OUTPUT_MODE_BY_DOMAIN.items()}


def _coerce_output_mode(mode: OutputMode | str) -> OutputMode:
    if isinstance(mode, OutputMode):
        return mode

    runtime_mode = DOMAIN_OUTPUT_MODE_BY_RUNTIME.get(mode)
    if runtime_mode is not None:
        return runtime_mode

    return OutputMode(mode)


@dataclass(slots=True, frozen=True)
class RuntimeCompatService:
    def load_config(self) -> app_services.AppConfig:
        return app_services.load_config()

    def write_config_value(self, key: str, value: Any) -> app_services.AppConfig:
        app_services.write_config_value(key, value)
        return app_services.load_config()

    def has_valid_steam_path(self, steam_path: str | None) -> bool:
        return app_services.is_existing_steam_path(steam_path)

    def session_settings_from_config(self, config: app_services.AppConfig | None = None) -> SessionSettings:
        loaded_config = config or self.load_config()
        return SessionSettings(
            steam_path=loaded_config.steam_path,
            output_path=loaded_config.output_path,
            batch_extract_workers=loaded_config.batch_extract_workers,
        )

    def extract_info_to_csv(self, steam_path: str | None = None, file_path: str | None = None) -> str:
        return app_services.extract_info_to_csv(steam_path=steam_path, file_path=file_path)

    def read_info_csv(self, file_path: str | None = None):
        return app_services.read_info_csv(file_path or app_services.INFO_CSV_FILE)

    def build_extraction_options(self, settings: SessionSettings) -> app_services.ExtractionOptions:
        output_mode = RUNTIME_OUTPUT_MODE_BY_DOMAIN[_coerce_output_mode(settings.output_mode)]
        return app_services.ExtractionOptions(
            steam_path=settings.steam_path,
            output_path=settings.output_path or app_services.DEFAULT_OUTPUT_PATH,
            output_mode=output_mode,
            not_convert_tex_to_image=settings.not_convert_tex_to_image,
            use_wallpaper_name_as_subdir=settings.use_wallpaper_name_as_subdir,
            copy_project_json_and_preview=settings.copy_project_json_and_preview,
            overwrite_files=settings.overwrite_files,
        )

    def build_extract_command(self, settings: SessionSettings, item_id: str, title: str) -> list[str]:
        return app_services.build_extract_command(self.build_extraction_options(settings), item_id, title)

    def run_extract_command(self, command: list[str]):
        return app_services.run_extract_command(command)

    def resolve_batch_extract_workers(self, configured_workers: int) -> int:
        return app_services.resolve_batch_extract_workers(configured_workers)

    def get_workshop_directory(self, steam_path: str) -> str:
        return app_services.get_workshop_directory(steam_path)

    def get_item_directory(self, steam_path: str, item_id: str) -> str:
        return app_services.get_item_directory(steam_path, item_id)

    def get_scene_pkg_path(self, steam_path: str, item_id: str) -> str:
        return app_services.get_scene_pkg_path(steam_path, item_id)

    @property
    def repkg_executable(self) -> str:
        return app_services.REPKG_EXECUTABLE
