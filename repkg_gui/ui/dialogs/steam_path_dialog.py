from __future__ import annotations

import os

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
)

from ...app_context import AppContext
from ...services.steam_locator_service import SteamLocatorService
from ..widgets.steam_path_selector import SteamPathSelector

def is_valid_steam_executable(path: str) -> bool:
    normalized = str(path or "").strip()
    return bool(normalized) and normalized.lower().endswith("steam.exe") and os.path.isfile(normalized)

class SteamPathSearchWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, locator_service: SteamLocatorService | None = None):
        super().__init__()
        self.locator_service = locator_service or SteamLocatorService()

    def run(self) -> None:
        try:
            result = self.locator_service.find_steam_path() or ""
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.failed.emit(str(exc))
            return
        self.finished.emit(result)


class SteamPathDialog(QDialog):
    def __init__(self, context: AppContext, parent=None):
        super().__init__(parent)
        self.context = context
        self._search_thread: QThread | None = None
        self._search_worker: SteamPathSearchWorker | None = None

        self.setWindowTitle("选择 steam.exe")
        self.setModal(True)
        self.resize(680, 220)

        layout = QVBoxLayout(self)
        description = QLabel(
            "请确认 steam.exe 路径。首次启动和后续从设置页修改路径时，都会复用这个对话框。"
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.selector = SteamPathSelector(initial_path=context.state.steam_path)
        self.selector.browse_requested.connect(self._browse_for_path)
        self.selector.auto_locate_requested.connect(self._start_auto_locate)
        self.selector.path_edited.connect(self._validate_path)
        layout.addWidget(self.selector)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("确认")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        self.button_box.accepted.connect(self._accept_selection)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self._validate_path(self.selector.path())

    def _browse_for_path(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 steam.exe",
            os.path.dirname(self.selector.path()) if self.selector.path() else "",
            "Steam executable (steam.exe);;Executable files (*.exe);;All files (*.*)",
        )
        if selected_path:
            self.selector.set_path(selected_path)

    def _start_auto_locate(self) -> None:
        if self._search_thread is not None:
            return

        self._set_searching(True)
        self.status_label.setText("正在搜索 steam.exe，请稍候…")

        self._search_thread = QThread(self)
        self._search_worker = SteamPathSearchWorker()
        self._search_worker.moveToThread(self._search_thread)
        self._search_thread.started.connect(self._search_worker.run)
        self._search_worker.finished.connect(self._handle_auto_locate_finished)
        self._search_worker.failed.connect(self._handle_auto_locate_failed)
        self._search_worker.finished.connect(self._search_thread.quit)
        self._search_worker.failed.connect(self._search_thread.quit)
        self._search_thread.finished.connect(self._cleanup_search_thread)
        self._search_thread.start()

    def _handle_auto_locate_finished(self, steam_path: str) -> None:
        if steam_path:
            self.selector.set_path(steam_path)
            self.status_label.setText("已自动定位到 steam.exe，请确认后继续。")
        else:
            self.status_label.setText("未自动找到 steam.exe，请手动浏览选择。")

    def _handle_auto_locate_failed(self, message: str) -> None:
        self.status_label.setText("搜索 steam.exe 时发生错误，请改为手动选择。")
        QMessageBox.warning(self, "搜索失败", message or "搜索 steam.exe 时发生未知错误。")

    def _cleanup_search_thread(self) -> None:
        if self._search_worker is not None:
            self._search_worker.deleteLater()
        if self._search_thread is not None:
            self._search_thread.deleteLater()
        self._search_worker = None
        self._search_thread = None
        self._set_searching(False)
        self._validate_path(self.selector.path())

    def _set_searching(self, searching: bool) -> None:
        self.selector.set_buttons_enabled(not searching)
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(not searching)

    def _validate_path(self, path: str) -> None:
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if not path.strip():
            self.status_label.setText("请选择或自动定位一个有效的 steam.exe 路径。")
            ok_button.setEnabled(False)
            return

        if is_valid_steam_executable(path):
            self.status_label.setText("路径有效，确认后会写入 runtime\\config.json。")
            ok_button.setEnabled(True)
            return

        self.status_label.setText("当前路径无效，请选择正确的 steam.exe。")
        ok_button.setEnabled(False)

    def _accept_selection(self) -> None:
        selected_path = self.selector.path()
        if not is_valid_steam_executable(selected_path):
            QMessageBox.warning(self, "路径错误", "请选择正确的 steam.exe 路径。")
            return

        self.context.set_steam_path(selected_path)
        self.accept()

    def reject(self) -> None:
        if self._search_thread is not None:
            QMessageBox.information(self, "请稍候", "正在搜索 steam.exe，请等待搜索完成。")
            return
        super().reject()
