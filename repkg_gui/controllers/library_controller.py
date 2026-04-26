from __future__ import annotations

import os

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices

from app_services import INFO_CSV_FILE, PROJECT_ROOT

from repkg_gui.app_context import AppContext
from repkg_gui.domain.entities import CatalogSnapshot, FilterState, WallpaperRecord
from repkg_gui.domain.enums import FilterField
from repkg_gui.models.catalog_filter_proxy import CatalogFilterProxyModel
from repkg_gui.models.catalog_table_model import CatalogTableModel
from repkg_gui.models.selection_model import (
    CatalogSelection,
    build_filter_status,
    build_loaded_status,
    build_selection_status,
    distinct_field_values,
    normalize_selection,
)
from repkg_gui.services.catalog_service import CatalogService
from repkg_gui.services.runtime_compat import RuntimeCompatService


class LibraryController(QObject):
    filter_options_changed = Signal(object)
    filter_state_changed = Signal(object)
    selection_changed = Signal(object)
    selection_summary_changed = Signal(str)
    detail_record_changed = Signal(object)
    footer_text_changed = Signal(str)
    view_mode_changed = Signal(str)
    single_extract_requested = Signal(str)
    batch_extract_requested = Signal(object)

    def __init__(
        self,
        context: AppContext,
        catalog_service: CatalogService | None = None,
        runtime: RuntimeCompatService | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.context = context
        self.runtime = runtime or RuntimeCompatService()
        self.catalog_service = catalog_service or CatalogService(runtime=self.runtime)
        self.table_model = CatalogTableModel(parent=self)
        self.filter_proxy_model = CatalogFilterProxyModel(self)
        self.filter_proxy_model.setSourceModel(self.table_model)
        self._selection = CatalogSelection()
        self._snapshot = CatalogSnapshot(steam_path=context.state.steam_path, csv_path="", records=())

    def initialize(self) -> None:
        self._emit_filter_options()
        self.filter_state_changed.emit(self.filter_proxy_model.filter_state())
        self.view_mode_changed.emit(self.context.state.view_mode)
        self._load_initial_catalog()

    def current_record(self) -> WallpaperRecord | None:
        if self._selection.focused_id:
            record = self.record_by_id(self._selection.focused_id)
            if record is not None:
                return record
        return self.filter_proxy_model.record_for_proxy_row(0)

    def total_count(self) -> int:
        return self.table_model.rowCount()

    def visible_count(self) -> int:
        return self.filter_proxy_model.rowCount()

    def record_by_id(self, item_id: str | None) -> WallpaperRecord | None:
        normalized_item_id = str(item_id or "").strip()
        if not normalized_item_id:
            return None

        for record in self.table_model.all_records():
            if record.id == normalized_item_id:
                return record
        return None

    def set_view_mode(self, view_mode: str) -> None:
        normalized_view_mode = "thumbnail" if view_mode == "thumbnail" else "list"
        self.context.set_view_mode(normalized_view_mode)
        if normalized_view_mode == "thumbnail":
            target_focus = self._selection.focused_id or self._first_visible_item_id()
            target_ids = (target_focus,) if target_focus else ()
            self._update_selection(target_ids, target_focus, announce=False)
        self.view_mode_changed.emit(normalized_view_mode)
        status_message = "已切换到列表模式。" if normalized_view_mode == "list" else "已切换到缩略图模式。"
        self.context.set_status(status_message)

    def set_filter_state(self, filter_state: FilterState) -> None:
        self.filter_proxy_model.set_filter_state(filter_state)
        self.filter_state_changed.emit(self.filter_proxy_model.filter_state())
        self._reset_selection_after_filter()
        self.context.set_status(
            build_filter_status(
                self.filter_proxy_model.filter_state().field,
                self.filter_proxy_model.filter_state().value,
                self.visible_count(),
                self.total_count(),
            )
        )
        self._emit_footer_text()

    def reset_filter(self) -> None:
        self.set_filter_state(FilterState(field=FilterField.TITLE, value=""))

    def refresh_catalog(self) -> None:
        if not self.context.has_valid_steam_path():
            self.context.set_status("steam.exe 路径无效，无法刷新壁纸数据。")
            return

        self.context.set_task_state("scanning")
        try:
            snapshot = self.catalog_service.scan_catalog(self.context.state.steam_path)
        except (FileNotFoundError, ValueError, OSError) as exc:
            self.context.set_status(f"刷新壁纸数据失败：{exc}")
        else:
            self._apply_snapshot(snapshot, refreshed=True)
        finally:
            self.context.set_task_state("idle")

    def select_all_visible(self) -> None:
        visible_ids = self.filter_proxy_model.visible_item_ids()
        if not visible_ids:
            self.context.set_status("当前没有可选中的壁纸。")
            return

        self._update_selection(visible_ids, visible_ids[0], announce=True)

    def handle_table_selection(self, item_ids: tuple[str, ...], focused_id: str | None) -> None:
        if self.context.state.view_mode != "list":
            return
        self._update_selection(item_ids, focused_id, announce=True)

    def handle_thumbnail_selection(self, item_id: str | None) -> None:
        if self.context.state.view_mode != "thumbnail":
            return
        focused_id = str(item_id or "").strip() or self._first_visible_item_id()
        selected_ids = (focused_id,) if focused_id else ()
        self._update_selection(selected_ids, focused_id, announce=True)

    def open_preview_for_item(self, item_id: str | None = None) -> None:
        record = self.record_by_id(item_id or self._selection.focused_id)
        if record is None or not record.preview_path or not os.path.exists(record.preview_path):
            self.context.set_status("当前项目没有可打开的预览文件。")
            return

        if QDesktopServices.openUrl(QUrl.fromLocalFile(record.preview_path)):
            self.context.set_status(f"已打开预览文件：{record.display_title}")
            return
        self.context.set_status("打开预览文件失败。")

    def open_folder_for_item(self, item_id: str | None = None) -> None:
        record = self.record_by_id(item_id or self._selection.focused_id)
        if record is None:
            self.context.set_status("当前没有可打开目录的壁纸。")
            return

        folder_path = self._resolve_record_folder(record)
        if not folder_path or not os.path.isdir(folder_path):
            self.context.set_status("当前项目没有可打开的壁纸目录。")
            return

        if QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path)):
            self.context.set_status(f"已打开壁纸目录：{record.display_title}")
            return
        self.context.set_status("打开壁纸目录失败。")

    def request_single_extract(self, item_id: str | None = None) -> None:
        record = self.record_by_id(item_id or self._selection.focused_id)
        if record is None:
            self.context.set_status("当前没有可提取的壁纸。")
            return

        self.single_extract_requested.emit(record.id)
        self.context.set_status(f"已触发单项提取请求：{record.display_title}")

    def request_batch_extract(self) -> None:
        selected_ids = self._selection.selected_ids
        if not selected_ids:
            self.context.set_status("请先在列表中选择需要批量提取的壁纸。")
            return

        self.batch_extract_requested.emit(selected_ids)
        self.context.set_status(f"已触发 {len(selected_ids)} 项壁纸的批量提取请求。")

    def _load_initial_catalog(self) -> None:
        if os.path.exists(INFO_CSV_FILE):
            try:
                snapshot = self.catalog_service.load_snapshot_from_csv(
                    INFO_CSV_FILE,
                    steam_path=self.context.state.steam_path,
                )
            except (FileNotFoundError, ValueError, OSError) as exc:
                self.context.set_status(f"读取壁纸缓存失败：{exc}")
            else:
                self._apply_snapshot(snapshot)
                return

        if self.context.has_valid_steam_path():
            self.refresh_catalog()
            return

        self.table_model.set_records(())
        self.context.set_catalog_records(())
        self._update_selection((), None, announce=False)
        self.context.state.last_scan_summary = "尚未加载壁纸数据。"
        self._emit_footer_text()
        self.context.set_status("尚未加载壁纸数据。请先设置 steam.exe 路径或点击刷新。")

    def _apply_snapshot(self, snapshot: CatalogSnapshot, refreshed: bool = False) -> None:
        self._snapshot = snapshot
        self.table_model.set_records(snapshot.records)
        self.context.set_catalog_records(snapshot.records)
        self.context.state.last_scan_summary = build_loaded_status(snapshot.total_count, refreshed=refreshed)
        self._emit_filter_options()
        self._reset_selection_after_filter()
        self._emit_footer_text()
        self.context.session_changed.emit()
        self.context.set_status(self.context.state.last_scan_summary)

    def _emit_filter_options(self) -> None:
        options_by_field = {
            field.value: distinct_field_values(self.table_model.all_records(), field)
            for field in (FilterField.TAGS, FilterField.TYPE)
        }
        self.filter_options_changed.emit(options_by_field)

    def _emit_footer_text(self) -> None:
        source_display = "未加载"
        if self._snapshot.csv_path:
            source_display = os.path.relpath(self._snapshot.csv_path, PROJECT_ROOT)
        footer_text = f"数据源：{source_display}｜显示 {self.visible_count()}/{self.total_count()} 项"
        self.footer_text_changed.emit(footer_text)

    def _first_visible_item_id(self) -> str | None:
        if self.filter_proxy_model.rowCount() <= 0:
            return None
        item_id = self.filter_proxy_model.index(0, CatalogTableModel.COLUMN_ID).data(CatalogTableModel.ITEM_ID_ROLE)
        normalized_item_id = str(item_id or "").strip()
        return normalized_item_id or None

    def _reset_selection_after_filter(self) -> None:
        focused_id = self._first_visible_item_id()
        selected_ids: tuple[str, ...] = ()
        if self.context.state.view_mode == "thumbnail" and focused_id:
            selected_ids = (focused_id,)
        self._update_selection(selected_ids, focused_id, announce=False)

    def _update_selection(
        self,
        item_ids: tuple[str, ...] | list[str],
        focused_id: str | None,
        announce: bool,
    ) -> None:
        visible_ids = set(self.filter_proxy_model.visible_item_ids())
        normalized_selection = normalize_selection(item_ids, focused_id)
        visible_selected_ids = tuple(item_id for item_id in normalized_selection.selected_ids if item_id in visible_ids)

        next_focus = normalized_selection.focused_id if normalized_selection.focused_id in visible_ids else None
        if next_focus is None:
            next_focus = visible_selected_ids[0] if visible_selected_ids else self._first_visible_item_id()

        self._selection = CatalogSelection(selected_ids=visible_selected_ids, focused_id=next_focus)
        self.context.state.selected_wallpaper_ids = set(visible_selected_ids)
        self.context.state.focused_wallpaper_id = next_focus
        self.selection_changed.emit(self._selection)
        self.selection_summary_changed.emit(build_selection_status(len(visible_selected_ids), self.visible_count()))
        self.detail_record_changed.emit(self.current_record())
        self.context.session_changed.emit()
        if announce:
            self.context.set_status(build_selection_status(len(visible_selected_ids), self.visible_count()))

    def _resolve_record_folder(self, record: WallpaperRecord) -> str:
        if record.preview_path:
            preview_folder = os.path.dirname(record.preview_path)
            if preview_folder:
                return preview_folder

        if self.context.state.steam_path and record.id:
            return self.runtime.get_item_directory(self.context.state.steam_path, record.id)

        return ""
