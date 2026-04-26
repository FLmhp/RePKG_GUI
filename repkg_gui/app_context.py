from __future__ import annotations

import os
from collections.abc import Iterable

from PySide6.QtCore import QObject, Signal

from app_services import (
    AppConfig,
    CUSTOM_THEME_PRESET,
    THEME_COLOR_KEYS,
    THEME_PRESETS,
    load_config,
    write_config_value,
    write_config_values,
)
from repkg_gui.domain.entities import SessionSettings, WallpaperRecord

from .state.session_state import SessionState


def is_valid_steam_path(path: str) -> bool:
    normalized = str(path or "").strip()
    return bool(normalized) and normalized.lower().endswith("steam.exe") and os.path.isfile(normalized)


class AppContext(QObject):
    config_changed = Signal()
    session_changed = Signal()
    catalog_changed = Signal()
    selection_changed = Signal()
    extraction_summary_changed = Signal(str)
    status_changed = Signal(str)
    steam_path_changed = Signal(str)

    def __init__(self, state: SessionState):
        super().__init__()
        self.state = state

    @classmethod
    def from_config(cls, config: AppConfig) -> "AppContext":
        return cls(SessionState.from_config(config))

    def has_valid_steam_path(self) -> bool:
        return is_valid_steam_path(self.state.steam_path)

    def refresh_config(self) -> None:
        self.state.config = load_config()
        self.config_changed.emit()
        self.session_changed.emit()

    def set_status(self, message: str) -> None:
        self.state.status_message = message
        self.status_changed.emit(message)

    def set_task_state(self, task_state: str) -> None:
        self.state.task_state = task_state
        self.session_changed.emit()

    def build_session_settings(self) -> SessionSettings:
        return SessionSettings(
            steam_path=self.state.steam_path,
            output_path=self.state.output_path,
            batch_extract_workers=self.state.batch_extract_workers,
            output_mode=self.state.output_mode,
            not_convert_tex_to_image=self.state.not_convert_tex_to_image,
            use_wallpaper_name_as_subdir=self.state.use_wallpaper_name_as_subdir,
            copy_project_json_and_preview=self.state.copy_project_json_and_preview,
            overwrite_files=self.state.overwrite_files,
        )

    def set_view_mode(self, view_mode: str) -> None:
        self.state.view_mode = view_mode
        self.session_changed.emit()

    def set_steam_path(self, steam_path: str) -> None:
        normalized = os.path.normpath(str(steam_path or "").strip()) if steam_path else ""
        write_config_value("steam_path", normalized)
        self.refresh_config()
        self.steam_path_changed.emit(self.state.steam_path)
        if self.has_valid_steam_path():
            self.set_status(f"已设置 steam.exe 路径：{self.state.steam_path}")
        else:
            self.set_status("steam.exe 路径无效，请重新选择。")

    def set_output_path(self, output_path: str) -> None:
        write_config_value("output_path", str(output_path or "").strip())
        self.refresh_config()
        self.set_status(f"已更新输出目录：{self.state.output_path}")

    def set_batch_extract_workers(self, workers: int) -> None:
        write_config_value("batch_extract_workers", int(workers))
        self.refresh_config()
        self.set_status(f"已更新批量提取并发：{self.state.batch_extract_workers}")

    def set_theme_preset(self, preset: str) -> None:
        normalized_preset = str(preset or "").strip().lower()
        if normalized_preset not in THEME_PRESETS and normalized_preset != CUSTOM_THEME_PRESET:
            raise KeyError(f"Unknown theme preset: {preset}")

        updates = {"theme_preset": normalized_preset}
        if normalized_preset in THEME_PRESETS:
            updates.update(THEME_PRESETS[normalized_preset])
        write_config_values(updates)
        self.refresh_config()
        self.set_status(f"已切换主题预设：{self.state.config.theme_preset}")

    def set_theme_color(self, color_name: str, color_value: str) -> None:
        if color_name not in THEME_COLOR_KEYS:
            raise KeyError(f"Unknown theme color: {color_name}")

        write_config_values({"theme_preset": CUSTOM_THEME_PRESET, color_name: color_value})
        self.refresh_config()
        self.set_status(f"已更新主题颜色：{color_name}")

    def set_output_mode(self, output_mode: str) -> None:
        self.state.output_mode = output_mode
        self.session_changed.emit()
        self.set_status(f"当前输出模式：{output_mode}")

    def set_catalog_records(self, records: Iterable[WallpaperRecord]) -> None:
        normalized_records = tuple(records)
        self.state.catalog_records = normalized_records
        self.state.catalog_count = len(normalized_records)
        valid_ids = {record.id for record in normalized_records if record.id}
        self.state.selected_wallpaper_ids.intersection_update(valid_ids)
        if self.state.focused_wallpaper_id not in valid_ids:
            self.state.focused_wallpaper_id = None
        self.catalog_changed.emit()
        self.session_changed.emit()

    def set_selected_wallpaper_ids(self, item_ids: Iterable[str]) -> None:
        self.state.selected_wallpaper_ids = {str(item_id).strip() for item_id in item_ids if str(item_id).strip()}
        self.selection_changed.emit()
        self.session_changed.emit()

    def set_focused_wallpaper_id(self, item_id: str | None) -> None:
        self.state.focused_wallpaper_id = str(item_id).strip() if item_id else None
        self.selection_changed.emit()
        self.session_changed.emit()

    def set_last_extraction_summary(self, summary: str) -> None:
        self.state.last_extraction_summary = summary
        self.extraction_summary_changed.emit(summary)
        self.session_changed.emit()

    def set_option(self, option_name: str, value: bool) -> None:
        if not hasattr(self.state, option_name):
            raise AttributeError(f"Unknown session option: {option_name}")
        setattr(self.state, option_name, bool(value))
        self.session_changed.emit()
