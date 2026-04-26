from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QMainWindow, QStatusBar, QTabWidget

from ..app_context import AppContext
from .dialogs.steam_path_dialog import SteamPathDialog
from .pages.about_page import AboutPage
from .pages.help_page import HelpPage
from .pages.library_page import LibraryPage
from .pages.settings_page import SettingsPage
from .widgets.status_strip import StatusStrip

if TYPE_CHECKING:
    from ..controllers.extraction_controller import ExtractionController


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext, extraction_controller: "ExtractionController | None" = None):
        super().__init__()
        self.context = context
        self.extraction_controller = extraction_controller
        self.setWindowTitle("RePKG_GUI")
        self.resize(1560, 860)
        self.setMinimumSize(1180, 680)

        self.tabs = QTabWidget()
        self.library_page = LibraryPage(context)
        self.settings_page = SettingsPage(context)
        self.help_page = HelpPage()
        self.about_page = AboutPage()

        self.tabs.addTab(self.library_page, "已安装壁纸")
        self.tabs.addTab(self.settings_page, "设置")
        self.tabs.addTab(self.help_page, "帮助")
        self.tabs.addTab(self.about_page, "关于")
        self.setCentralWidget(self.tabs)

        status_bar = QStatusBar(self)
        status_bar.setSizeGripEnabled(False)
        self.setStatusBar(status_bar)
        self.status_strip = StatusStrip(context)
        status_bar.addPermanentWidget(self.status_strip, 1)

        self.settings_page.change_steam_path_requested.connect(self.open_steam_path_dialog)
        self.tabs.currentChanged.connect(self._handle_tab_changed)
        if self.extraction_controller is not None:
            self.register_extraction_controller(self.extraction_controller)

    def open_steam_path_dialog(self) -> None:
        dialog = SteamPathDialog(self.context, parent=self)
        dialog.exec()

    def register_extraction_controller(self, controller: "ExtractionController") -> None:
        self.extraction_controller = controller
        self.library_page.single_extract_requested.connect(
            lambda item_id, records: controller.extract_single(item_id, records=records, parent=self)
        )
        self.library_page.batch_extract_requested.connect(
            lambda item_ids, records: controller.extract_batch(item_ids, records=records, parent=self)
        )

    def _handle_tab_changed(self, index: int) -> None:
        tab_text = self.tabs.tabText(index)
        self.context.set_status(f"当前位于 {tab_text} 标签页。")
