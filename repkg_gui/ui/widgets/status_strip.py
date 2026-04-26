from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ...app_context import AppContext

TASK_STATE_LABELS = {
    "idle": "空闲",
    "scanning": "扫描中",
    "extracting": "提取中",
}


class StatusStrip(QWidget):
    def __init__(self, context: AppContext):
        super().__init__()
        self.context = context

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.task_label = QLabel()
        self.message_label = QLabel()
        self.message_label.setMinimumWidth(360)

        layout.addWidget(QLabel("状态："))
        layout.addWidget(self.task_label)
        layout.addWidget(QLabel("消息："))
        layout.addWidget(self.message_label, 1)

        self.context.status_changed.connect(self._update_message)
        self.context.session_changed.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        self.task_label.setText(TASK_STATE_LABELS.get(self.context.state.task_state, self.context.state.task_state))
        self.message_label.setText(self.context.state.status_message)

    def _update_message(self, message: str) -> None:
        self.message_label.setText(message)
