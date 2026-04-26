from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget


class SteamPathSelector(QWidget):
    browse_requested = Signal()
    auto_locate_requested = Signal()
    path_edited = Signal(str)

    def __init__(
        self,
        label_text: str = "steam.exe 路径：",
        initial_path: str = "",
        read_only: bool = False,
        show_buttons: bool = True,
        show_label: bool = True,
    ):
        super().__init__()
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(6)

        if show_label:
            outer_layout.addWidget(QLabel(label_text))

        row_layout = QHBoxLayout()
        self.path_edit = QLineEdit(initial_path)
        self.path_edit.setReadOnly(read_only)
        self.path_edit.setPlaceholderText(r"C:\Program Files (x86)\Steam\steam.exe")
        row_layout.addWidget(self.path_edit, 1)

        self.browse_button = QPushButton("浏览")
        self.auto_locate_button = QPushButton("自动定位")
        self.browse_button.setVisible(show_buttons)
        self.auto_locate_button.setVisible(show_buttons)
        row_layout.addWidget(self.browse_button)
        row_layout.addWidget(self.auto_locate_button)

        outer_layout.addLayout(row_layout)

        self.path_edit.textChanged.connect(self.path_edited.emit)
        self.browse_button.clicked.connect(self.browse_requested.emit)
        self.auto_locate_button.clicked.connect(self.auto_locate_requested.emit)

    def path(self) -> str:
        return self.path_edit.text().strip()

    def set_path(self, path: str) -> None:
        self.path_edit.setText(path)

    def set_buttons_enabled(self, enabled: bool) -> None:
        self.browse_button.setEnabled(enabled)
        self.auto_locate_button.setEnabled(enabled)
