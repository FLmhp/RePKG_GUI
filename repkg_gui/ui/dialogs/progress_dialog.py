from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout


class ProgressDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._running = False

        self.setWindowTitle("提取进度")
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)

        layout = QVBoxLayout(self)
        self.summary_label = QLabel("等待开始…")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        self.detail_label = QLabel("")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        self.item_label = QLabel("")
        self.item_label.setWordWrap(True)
        layout.addWidget(self.item_label)

    def set_running(self, running: bool) -> None:
        self._running = running

    def set_progress(
        self,
        completed: int,
        total: int,
        message: str,
        current_item_id: str = "",
        worker_count: int = 0,
    ) -> None:
        safe_total = max(total, 1)
        bounded_completed = min(max(completed, 0), safe_total)
        self.progress_bar.setRange(0, safe_total)
        self.progress_bar.setValue(bounded_completed)
        self.summary_label.setText(message)

        detail_parts = [f"已处理 {min(completed, total) if total else completed}/{total} 项"]
        if worker_count > 1:
            detail_parts.append(f"并发 {worker_count} 线程")
        self.detail_label.setText("，".join(detail_parts))

        if current_item_id:
            self.item_label.setText(f"当前项目：{current_item_id}")
        else:
            self.item_label.setText("")

    def closeEvent(self, event: QCloseEvent) -> None:  # pragma: no cover - UI behavior
        if self._running:
            event.ignore()
            return
        super().closeEvent(event)
