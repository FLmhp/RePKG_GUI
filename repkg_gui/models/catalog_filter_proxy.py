from __future__ import annotations

from PySide6.QtCore import QModelIndex, QSortFilterProxyModel, Qt

from repkg_gui.domain.entities import FilterState, WallpaperRecord
from repkg_gui.domain.enums import FilterField
from repkg_gui.models.catalog_table_model import CatalogTableModel


class CatalogFilterProxyModel(QSortFilterProxyModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._filter_state = FilterState()
        self.setDynamicSortFilter(True)
        self.setSortCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if role == int(Qt.ItemDataRole.DisplayRole) and index.isValid() and index.column() == CatalogTableModel.COLUMN_INDEX:
            return index.row() + 1
        return super().data(index, role)

    def filter_state(self) -> FilterState:
        return self._filter_state

    def set_filter_state(self, filter_state: FilterState) -> None:
        normalized_state = FilterState(field=filter_state.field, value=filter_state.value.strip())
        if normalized_state == self._filter_state:
            return
        self.beginFilterChange()
        self._filter_state = normalized_state
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        source_model = self.sourceModel()
        if not isinstance(source_model, CatalogTableModel):
            return True

        record = source_model.record_at(source_row)
        if record is None or not self._filter_state.is_active:
            return record is not None

        keyword = self._filter_state.value.casefold()
        if self._filter_state.field is FilterField.TITLE:
            return keyword in record.display_title.casefold()
        if self._filter_state.field is FilterField.TAGS:
            return any(keyword in tag.casefold() for tag in record.tags)
        return keyword in record.type.casefold()

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        if left.column() in (CatalogTableModel.COLUMN_INDEX, CatalogTableModel.COLUMN_ID):
            left_value = str(left.data(Qt.ItemDataRole.DisplayRole) or "").strip()
            right_value = str(right.data(Qt.ItemDataRole.DisplayRole) or "").strip()
            if left_value.isdigit() and right_value.isdigit():
                return int(left_value) < int(right_value)

        left_text = str(left.data(Qt.ItemDataRole.DisplayRole) or "").casefold()
        right_text = str(right.data(Qt.ItemDataRole.DisplayRole) or "").casefold()
        return left_text < right_text

    def visible_item_ids(self) -> tuple[str, ...]:
        return tuple(
            str(self.index(row, CatalogTableModel.COLUMN_ID).data(CatalogTableModel.ITEM_ID_ROLE) or "")
            for row in range(self.rowCount())
        )

    def visible_records(self) -> tuple[WallpaperRecord, ...]:
        records: list[WallpaperRecord] = []
        for row in range(self.rowCount()):
            record = self.record_for_proxy_row(row)
            if record is not None:
                records.append(record)
        return tuple(records)

    def record_for_proxy_row(self, row: int) -> WallpaperRecord | None:
        if row < 0 or row >= self.rowCount():
            return None
        record = self.index(row, CatalogTableModel.COLUMN_TITLE).data(CatalogTableModel.RECORD_ROLE)
        if isinstance(record, WallpaperRecord):
            return record
        return None

    def record_for_proxy_index(self, index: QModelIndex) -> WallpaperRecord | None:
        if not index.isValid():
            return None
        return self.record_for_proxy_row(index.row())

    def find_row_by_id(self, item_id: str) -> int:
        normalized_item_id = str(item_id or "").strip()
        if not normalized_item_id:
            return -1

        for row in range(self.rowCount()):
            current_item_id = str(
                self.index(row, CatalogTableModel.COLUMN_ID).data(CatalogTableModel.ITEM_ID_ROLE) or ""
            )
            if current_item_id == normalized_item_id:
                return row
        return -1
