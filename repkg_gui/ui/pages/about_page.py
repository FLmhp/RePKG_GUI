from __future__ import annotations

import os

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from ...controllers.settings_controller import (
    AboutMetadata,
    load_about_metadata,
)


class ClickableImageLabel(QLabel):
    clicked = Signal()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class AboutPage(QWidget):
    def __init__(self):
        super().__init__()
        metadata = load_about_metadata()

        outer_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        app_box = QGroupBox("RePKG_GUI")
        app_layout = QVBoxLayout(app_box)
        app_summary = QLabel("这是一个给 Wallpaper Engine 本地创意工坊壁纸用的小工具，主要做扫描、筛选、预览和提取。")
        app_summary.setWordWrap(True)
        app_layout.addWidget(app_summary)
        app_layout.addWidget(QLabel(f"版本：{metadata.app_version}"))
        author_link = self._build_link_label("作者主页：", metadata.app_author, metadata.app_author_url)
        app_layout.addWidget(author_link)
        content_layout.addWidget(app_box)

        repkg_box = QGroupBox("RePKG")
        repkg_layout = QVBoxLayout(repkg_box)
        repkg_layout.addWidget(QLabel(f"版本：{metadata.repkg_version}"))
        repkg_layout.addWidget(QLabel(f"作者：{metadata.repkg_author}"))
        repkg_link = self._build_link_label("项目地址：", metadata.repkg_project_url, metadata.repkg_project_url)
        repkg_layout.addWidget(repkg_link)
        content_layout.addWidget(repkg_box)

        image_box = QGroupBox("支持作者")
        image_layout = QVBoxLayout(image_box)
        image_hint = QLabel("点击下方图片会跳转至收款码截图。")
        image_hint.setWordWrap(True)
        image_layout.addWidget(image_hint)
        image_label = ClickableImageLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pixmap = QPixmap(metadata.support_image_path)
        if not pixmap.isNull():
            image_label.setPixmap(
                pixmap.scaled(
                    260,
                    260,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            image_label.setCursor(Qt.CursorShape.PointingHandCursor)
            image_label.clicked.connect(lambda: self._open_url(metadata.support_image_url))
        else:
            image_label.setText("未找到 nekomusume.png。")
        image_layout.addWidget(image_label)
        content_layout.addWidget(image_box)

        content_layout.addStretch(1)
        scroll_area.setWidget(content)
        outer_layout.addWidget(scroll_area)

    def _open_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    @staticmethod
    def _build_link_label(prefix: str, text: str, url: str) -> QLabel:
        label = QLabel(f"{prefix}<a href=\"{url}\">{text}</a>")
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)
        return label
