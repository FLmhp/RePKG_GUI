from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from repkg_gui.domain.entities import WallpaperRecord
from repkg_gui.models.selection_model import format_visibility


class CatalogTableModel(QAbstractTableModel):
    COLUMN_INDEX = 0
    COLUMN_TITLE = 1
    COLUMN_TAGS = 2
    COLUMN_TYPE = 3
    COLUMN_VISIBILITY = 4
    COLUMN_ID = 5

    RECORD_ROLE = int(Qt.ItemDataRole.UserRole) + 1
    ITEM_ID_ROLE = RECORD_ROLE + 1
    PREVIEW_PATH_ROLE = RECORD_ROLE + 2
    TITLE_ROLE = RECORD_ROLE + 3
    TAGS_ROLE = RECORD_ROLE + 4
    FILE_ROLE = RECORD_ROLE + 5

    HEADERS = ("#", "标题", "标签", "类型", "可见性", "ID")

    def __init__(self, records: Sequence[WallpaperRecord] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._records: tuple[WallpaperRecord, ...] = tuple(records or ())

    def set_records(self, records: Sequence[WallpaperRecord]) -> None:
        self.beginResetModel()
        self._records = tuple(records)
        self.endResetModel()

    def all_records(self) -> tuple[WallpaperRecord, ...]:
        return self._records

    def record_at(self, row: int) -> WallpaperRecord | None:
        if 0 <= row < len(self._records):
            return self._records[row]
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._records)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if role != int(Qt.ItemDataRole.DisplayRole):
            return None
        if orientation == Qt.Orientation.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        if orientation == Qt.Orientation.Vertical:
            return section + 1
        return None

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)):
        if not index.isValid():
            return None

        record = self.record_at(index.row())
        if record is None:
            return None

        if role == self.RECORD_ROLE:
            return record
        if role == self.ITEM_ID_ROLE:
            return record.id
        if role == self.PREVIEW_PATH_ROLE:
            return record.preview_path
        if role == self.TITLE_ROLE:
            return record.display_title
        if role == self.TAGS_ROLE:
            return record.tags_text
        if role == self.FILE_ROLE:
            return record.file

        if role == int(Qt.ItemDataRole.DisplayRole):
            if index.column() == self.COLUMN_INDEX:
                return index.row() + 1
            if index.column() == self.COLUMN_TITLE:
                return record.display_title
            if index.column() == self.COLUMN_TAGS:
                return record.tags_text
            if index.column() == self.COLUMN_TYPE:
                return record.type or "未标注"
            if index.column() == self.COLUMN_VISIBILITY:
                return format_visibility(record.visibility)
            if index.column() == self.COLUMN_ID:
                return record.id

        if role == int(Qt.ItemDataRole.TextAlignmentRole):
            if index.column() in (self.COLUMN_TITLE, self.COLUMN_TAGS):
                return int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            return int(Qt.AlignmentFlag.AlignCenter)

        return None
