from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel, QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMenu, QPushButton, QStackedWidget, QTableView, QToolButton, QVBoxLayout, QWidget

from ...app_context import AppContext
from ...controllers.library_controller import LibraryController
from ...models.catalog_table_model import CatalogTableModel
from ...models.selection_model import CatalogSelection
from ..widgets.details_panel import DetailsPanel
from ..widgets.filter_bar import FilterBar
from ..widgets.thumbnail_view import ThumbnailView


class LibraryPage(QWidget):
    single_extract_requested = Signal(str, object)
    batch_extract_requested = Signal(object, object)

    def __init__(self, context: AppContext):
        super().__init__()
        self.context = context
        self.controller = LibraryController(context, parent=self)
        self._syncing_selection = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)

        toolbar_layout = QHBoxLayout()
        self.list_mode_button = QToolButton()
        self.list_mode_button.setText("列表模式")
        self.list_mode_button.setCheckable(True)
        self.thumbnail_mode_button = QToolButton()
        self.thumbnail_mode_button.setText("缩略图模式")
        self.thumbnail_mode_button.setCheckable(True)
        self.refresh_button = QPushButton("刷新数据")

        toolbar_layout.addWidget(self.list_mode_button)
        toolbar_layout.addWidget(self.thumbnail_mode_button)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self.refresh_button)
        root_layout.addLayout(toolbar_layout)

        self.filter_bar = FilterBar()
        root_layout.addWidget(self.filter_bar)

        content_layout = QHBoxLayout()
        self.content_layout = content_layout
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self._build_table_view())
        self.content_stack.addWidget(self._build_thumbnail_view())
        content_layout.addWidget(self.content_stack, 3)
        self.details_panel = DetailsPanel()
        content_layout.addWidget(self.details_panel, 2)
        root_layout.addLayout(content_layout, 1)

        self.footer_label = QLabel("数据源：未加载｜显示 0/0 项")
        self.footer_label.setWordWrap(True)
        root_layout.addWidget(self.footer_label)

        self.list_mode_button.clicked.connect(lambda: self.controller.set_view_mode("list"))
        self.thumbnail_mode_button.clicked.connect(lambda: self.controller.set_view_mode("thumbnail"))
        self.refresh_button.clicked.connect(self.controller.refresh_catalog)
        self.filter_bar.filter_changed.connect(self.controller.set_filter_state)
        self.filter_bar.reset_requested.connect(self.controller.reset_filter)
        self.filter_bar.select_all_requested.connect(self.controller.select_all_visible)
        self.filter_bar.batch_extract_requested.connect(self.controller.request_batch_extract)
        self.details_panel.preview_requested.connect(self.controller.open_preview_for_item)
        self.details_panel.open_folder_requested.connect(self.controller.open_folder_for_item)
        self.details_panel.extract_requested.connect(self.controller.request_single_extract)
        self.thumbnail_view.preview_requested.connect(self.controller.open_preview_for_item)
        self.thumbnail_view.open_folder_requested.connect(self.controller.open_folder_for_item)
        self.thumbnail_view.extract_requested.connect(self.controller.request_single_extract)

        self.controller.filter_options_changed.connect(self.filter_bar.set_filter_options)
        self.controller.filter_state_changed.connect(self.filter_bar.set_filter_state)
        self.controller.selection_changed.connect(self._apply_selection_to_views)
        self.controller.selection_summary_changed.connect(self.details_panel.set_selection_summary)
        self.controller.detail_record_changed.connect(self.details_panel.set_record)
        self.controller.footer_text_changed.connect(self.footer_label.setText)
        self.controller.view_mode_changed.connect(self._apply_view_mode)
        self.controller.single_extract_requested.connect(
            lambda item_id: self.single_extract_requested.emit(item_id, self.controller.table_model.all_records())
        )
        self.controller.batch_extract_requested.connect(
            lambda item_ids: self.batch_extract_requested.emit(item_ids, self.controller.table_model.all_records())
        )

        self.table_view.selectionModel().selectionChanged.connect(self._handle_table_selection_changed)
        self.table_view.selectionModel().currentChanged.connect(self._handle_table_selection_changed)
        self.thumbnail_view.selectionModel().selectionChanged.connect(self._handle_thumbnail_selection_changed)
        self.thumbnail_view.selectionModel().currentChanged.connect(self._handle_thumbnail_selection_changed)

        self.controller.initialize()

    def _build_table_view(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        self.table_view = QTableView()
        self.table_view.setModel(self.controller.filter_proxy_model)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.sortByColumn(CatalogTableModel.COLUMN_TITLE, Qt.SortOrder.AscendingOrder)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.ExtendedSelection)
        self.table_view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.horizontalHeader().setStretchLastSection(False)
        self.table_view.horizontalHeader().setSectionResizeMode(
            CatalogTableModel.COLUMN_TITLE,
            self.table_view.horizontalHeader().ResizeMode.Stretch,
        )
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_table_context_menu)
        self.table_view.doubleClicked.connect(
            lambda index: self.controller.open_preview_for_item(self._item_id_from_index(index))
        )
        layout.addWidget(self.table_view)
        return container

    def _build_thumbnail_view(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        hint_label = QLabel("缩略图模式与列表共享同一份筛选结果和当前焦点。")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        self.thumbnail_view = ThumbnailView()
        self.thumbnail_view.setModel(self.controller.filter_proxy_model)
        layout.addWidget(self.thumbnail_view, 1)
        return container

    def _apply_view_mode(self, view_mode: str) -> None:
        is_list_mode = view_mode == "list"
        with QSignalBlocker(self.list_mode_button):
            self.list_mode_button.setChecked(is_list_mode)
        with QSignalBlocker(self.thumbnail_mode_button):
            self.thumbnail_mode_button.setChecked(not is_list_mode)
        self.content_stack.setCurrentIndex(0 if is_list_mode else 1)
        self.content_layout.setStretch(0, 3 if is_list_mode else 4)
        self.content_layout.setStretch(1, 2 if is_list_mode else 1)
        self.filter_bar.set_list_mode(is_list_mode)
        self.details_panel.set_view_mode(view_mode)

    def _handle_table_selection_changed(self, *_args) -> None:
        if self._syncing_selection:
            return
        selected_ids = tuple(self._item_id_from_index(index) for index in self.table_view.selectionModel().selectedRows())
        focused_id = self._item_id_from_index(self.table_view.currentIndex())
        self.controller.handle_table_selection(selected_ids, focused_id)

    def _handle_thumbnail_selection_changed(self, *_args) -> None:
        if self._syncing_selection:
            return
        self.controller.handle_thumbnail_selection(self._item_id_from_index(self.thumbnail_view.currentIndex()))

    def _apply_selection_to_views(self, selection: CatalogSelection) -> None:
        self._syncing_selection = True
        try:
            self._apply_table_selection(selection)
            self._apply_thumbnail_selection(selection)
        finally:
            self._syncing_selection = False

    def _apply_table_selection(self, selection: CatalogSelection) -> None:
        selection_model = self.table_view.selectionModel()
        if selection_model is None:
            return

        with QSignalBlocker(selection_model):
            selection_model.clearSelection()
            for item_id in selection.selected_ids:
                row = self.controller.filter_proxy_model.find_row_by_id(item_id)
                if row < 0:
                    continue
                index = self.controller.filter_proxy_model.index(row, CatalogTableModel.COLUMN_TITLE)
                selection_model.select(
                    index,
                    QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
                )

            focused_row = self.controller.filter_proxy_model.find_row_by_id(selection.focused_id or "")
            if focused_row >= 0:
                focused_index = self.controller.filter_proxy_model.index(focused_row, CatalogTableModel.COLUMN_TITLE)
                selection_model.setCurrentIndex(focused_index, QItemSelectionModel.SelectionFlag.NoUpdate)
                self.table_view.scrollTo(focused_index)

    def _apply_thumbnail_selection(self, selection: CatalogSelection) -> None:
        selection_model = self.thumbnail_view.selectionModel()
        if selection_model is None:
            return

        with QSignalBlocker(selection_model):
            selection_model.clearSelection()
            focused_row = self.controller.filter_proxy_model.find_row_by_id(selection.focused_id or "")
            if focused_row < 0:
                return
            focused_index = self.controller.filter_proxy_model.index(focused_row, CatalogTableModel.COLUMN_TITLE)
            selection_model.setCurrentIndex(
                focused_index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect,
            )
            self.thumbnail_view.scrollTo(focused_index)

    def _show_table_context_menu(self, position) -> None:
        index = self.table_view.indexAt(position)
        if not index.isValid():
            return

        item_id = self._item_id_from_index(index)
        if not item_id:
            return

        menu = QMenu(self)
        preview_action = menu.addAction("打开预览")
        open_folder_action = menu.addAction("打开文件夹")
        extract_action = menu.addAction("提取当前壁纸")
        batch_action = None
        if len(self.context.state.selected_wallpaper_ids) > 1:
            batch_action = menu.addAction("批量提取已选壁纸")

        chosen_action = menu.exec(self.table_view.viewport().mapToGlobal(position))
        if chosen_action == preview_action:
            self.controller.open_preview_for_item(item_id)
        elif chosen_action == open_folder_action:
            self.controller.open_folder_for_item(item_id)
        elif chosen_action == extract_action:
            self.controller.request_single_extract(item_id)
        elif batch_action is not None and chosen_action == batch_action:
            self.controller.request_batch_extract()

    @staticmethod
    def _item_id_from_index(index) -> str:
        if index is None or not index.isValid():
            return ""
        return str(index.data(CatalogTableModel.ITEM_ID_ROLE) or "")
