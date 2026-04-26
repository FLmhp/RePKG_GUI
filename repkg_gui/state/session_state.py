from __future__ import annotations

from dataclasses import dataclass, field

from app_services import AppConfig, SEPARATE_OUTPUT_MODE
from repkg_gui.domain.entities import WallpaperRecord


@dataclass
class SessionState:
    config: AppConfig
    view_mode: str = "list"
    output_mode: str = SEPARATE_OUTPUT_MODE
    not_convert_tex_to_image: bool = False
    use_wallpaper_name_as_subdir: bool = True
    copy_project_json_and_preview: bool = False
    overwrite_files: bool = True
    status_message: str = "准备就绪。"
    task_state: str = "idle"
    catalog_count: int = 0
    catalog_records: tuple[WallpaperRecord, ...] = field(default_factory=tuple)
    selected_wallpaper_ids: set[str] = field(default_factory=set)
    focused_wallpaper_id: str | None = None
    last_scan_summary: str = ""
    last_extraction_summary: str = ""

    @classmethod
    def from_config(cls, config: AppConfig) -> "SessionState":
        return cls(config=config)

    @property
    def steam_path(self) -> str:
        return self.config.steam_path

    @property
    def output_path(self) -> str:
        return self.config.output_path

    @property
    def batch_extract_workers(self) -> int:
        return self.config.batch_extract_workers
