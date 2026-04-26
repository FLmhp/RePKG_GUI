from __future__ import annotations

import os

from PySide6.QtCore import QModelIndex, QRect, QSize, Qt, Signal
from PySide6.QtGui import QImage, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import QListView, QMenu, QStyledItemDelegate, QStyle, QStyleOptionViewItem

from repkg_gui.image_utils import load_static_pixmap
from repkg_gui.models.catalog_table_model import CatalogTableModel
from repkg_gui.models.thumbnail_cache import ThumbnailCache
from repkg_gui.workers.thumbnail_loader import ThumbnailLoader

THUMBNAIL_SIZE = QSize(198, 156)
ITEM_SIZE = QSize(216, 176)
DEFAULT_COLUMN_COUNT = 4
MIN_COLUMN_WIDTH = 198
PREFERRED_COLUMN_WIDTH = 216


class _ThumbnailDelegate(QStyledItemDelegate):
    def __init__(self, view: "ThumbnailView") -> None:
        super().__init__(view)
        self._view = view

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        _ = option, index
        return ITEM_SIZE

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        painter.save()
        rect = option.rect.adjusted(1, 1, -1, -1)

        if option.state & QStyle.StateFlag.State_Selected:
            background_color = option.palette.color(QPalette.ColorRole.Highlight)
            background_color.setAlpha(38)
            painter.setBrush(background_color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(rect, 6, 6)

        thumbnail_rect = rect.adjusted(4, 4, -4, -4)
        pixmap = self._view.thumbnail_for_index(index, thumbnail_rect.size())
        target_rect = QRect(0, 0, pixmap.width(), pixmap.height())
        target_rect.moveCenter(thumbnail_rect.center())
        painter.drawPixmap(target_rect.topLeft(), pixmap)
        painter.restore()


class ThumbnailView(QListView):
    preview_requested = Signal(str)
    open_folder_requested = Signal(str)
    extract_requested = Signal(str)

    def __init__(
        self,
        cache: ThumbnailCache | None = None,
        loader: ThumbnailLoader | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._cache = cache or ThumbnailCache()
        self._loader = loader or ThumbnailLoader(parent=self)
        self._column_count = DEFAULT_COLUMN_COUNT

        self.setViewMode(QListView.ViewMode.IconMode)
        self.setMovement(QListView.Movement.Static)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setLayoutMode(QListView.LayoutMode.SinglePass)
        self.setUniformItemSizes(False)
        self.setWrapping(True)
        self.setSelectionMode(QListView.SelectionMode.SingleSelection)
        self.setSpacing(2)
        self.setMouseTracking(True)
        self.setItemDelegate(_ThumbnailDelegate(self))
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._update_grid_size()

        self.customContextMenuRequested.connect(self._show_context_menu)
        self.doubleClicked.connect(self._handle_double_clicked)
        self._loader.thumbnail_loaded.connect(self._handle_thumbnail_loaded)
        self._loader.thumbnail_failed.connect(self._handle_thumbnail_failed)

    def thumbnail_for_index(self, index: QModelIndex, size: QSize) -> QPixmap:
        preview_path = str(index.data(CatalogTableModel.PREVIEW_PATH_ROLE) or "")
        cache_key = ThumbnailCache.build_key(preview_path, size)
        cached_pixmap = self._cache.get(cache_key)
        if cached_pixmap is not None:
            return cached_pixmap

        placeholder = self._cache.placeholder(size)
        if preview_path and preview_path.lower().endswith(".gif") and os.path.exists(preview_path):
            pixmap = load_static_pixmap(preview_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._cache.store(cache_key, scaled_pixmap)
                return scaled_pixmap
        if preview_path and os.path.exists(preview_path) and self._cache.mark_pending(cache_key):
            self._loader.request(cache_key, preview_path, size)
        return placeholder

    def item_id_for_index(self, index: QModelIndex) -> str:
        if not index.isValid():
            return ""
        return str(index.data(CatalogTableModel.ITEM_ID_ROLE) or "")

    def _handle_double_clicked(self, index: QModelIndex) -> None:
        item_id = self.item_id_for_index(index)
        if item_id:
            self.preview_requested.emit(item_id)

    def _show_context_menu(self, position) -> None:
        index = self.indexAt(position)
        if not index.isValid():
            return

        self.setCurrentIndex(index)
        item_id = self.item_id_for_index(index)
        if not item_id:
            return

        menu = QMenu(self)
        preview_action = menu.addAction("打开预览")
        open_folder_action = menu.addAction("打开文件夹")
        extract_action = menu.addAction("提取当前壁纸")
        chosen_action = menu.exec(self.viewport().mapToGlobal(position))
        if chosen_action == preview_action:
            self.preview_requested.emit(item_id)
        elif chosen_action == open_folder_action:
            self.open_folder_requested.emit(item_id)
        elif chosen_action == extract_action:
            self.extract_requested.emit(item_id)

    def _handle_thumbnail_loaded(self, cache_key: str, image: object) -> None:
        if not isinstance(image, QImage):
            self._cache.clear_pending(cache_key)
            return
        self._cache.store(cache_key, QPixmap.fromImage(image))
        self.viewport().update()

    def _handle_thumbnail_failed(self, cache_key: str) -> None:
        self._cache.clear_pending(cache_key)
        self.viewport().update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_grid_size()

    def _update_grid_size(self) -> None:
        viewport_width = self.viewport().width()
        if viewport_width <= 0:
            viewport_width = PREFERRED_COLUMN_WIDTH * DEFAULT_COLUMN_COUNT
        spacing = self.spacing()
        self._column_count = max(1, viewport_width // PREFERRED_COLUMN_WIDTH)
        available_width = max(
            viewport_width - max(self._column_count - 1, 0) * spacing,
            MIN_COLUMN_WIDTH * self._column_count,
        )
        cell_width = max(MIN_COLUMN_WIDTH, available_width // self._column_count)
        self.setGridSize(QSize(cell_width, ITEM_SIZE.height()))
