from __future__ import annotations

from PySide6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from ...controllers.settings_controller import build_help_sections

class HelpPage(QWidget):
    def __init__(self):
        super().__init__()
        outer_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        for section in build_help_sections():
            section_box = QGroupBox(section.title)
            section_layout = QVBoxLayout(section_box)
            for line in section.lines:
                label = QLabel(line)
                label.setWordWrap(True)
                section_layout.addWidget(label)
            content_layout.addWidget(section_box)

        content_layout.addStretch(1)
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)
