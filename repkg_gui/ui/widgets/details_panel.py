from __future__ import annotations

import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMovie, QPixmap
from PySide6.QtWidgets import QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from repkg_gui.image_utils import load_static_pixmap
from repkg_gui.domain.entities import WallpaperRecord
from repkg_gui.models.selection_model import metadata_lines


class DetailsPanel(QWidget):
    preview_requested = Signal(str)
    open_folder_requested = Signal(str)
    extract_requested = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._record: WallpaperRecord | None = None
        self._preview_source: QPixmap | None = None
        self._preview_movie: QMovie | None = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)

        self.selection_summary_label = QLabel("当前未选择项目，当前列表共 0 项。")
        self.selection_summary_label.setWordWrap(True)
        root_layout.addWidget(self.selection_summary_label)

        preview_group = QGroupBox("预览")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(12, 12, 12, 12)
        self.preview_label = QLabel("暂无预览")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumHeight(320)
        self.preview_label.setWordWrap(True)
        preview_layout.addWidget(self.preview_label)
        root_layout.addWidget(preview_group)

        details_group = QGroupBox("详情")
        details_layout = QFormLayout(details_group)
        details_layout.setLabelAlignment(Qt.AlignmentFlag.AlignTop)
        self.title_label = QLabel("标题：")
        self.title_value = QLabel("未选中壁纸")
        self.title_value.setWordWrap(True)
        self.metadata_label = QLabel("信息：")
        self.metadata_value = QLabel("请从列表或缩略图中选择壁纸。")
        self.metadata_value.setWordWrap(True)
        details_layout.addRow(self.title_label, self.title_value)
        details_layout.addRow(self.metadata_label, self.metadata_value)
        root_layout.addWidget(details_group)

        action_layout = QHBoxLayout()
        self.preview_button = QPushButton("打开预览")
        self.open_folder_button = QPushButton("打开文件夹")
        self.extract_button = QPushButton("提取当前壁纸")
        action_layout.addWidget(self.preview_button)
        action_layout.addWidget(self.open_folder_button)
        action_layout.addWidget(self.extract_button)
        root_layout.addLayout(action_layout)
        root_layout.addStretch(1)

        self.preview_button.clicked.connect(self._emit_preview_requested)
        self.open_folder_button.clicked.connect(self._emit_open_folder_requested)
        self.extract_button.clicked.connect(self._emit_extract_requested)
        self.set_record(None)

    def set_view_mode(self, view_mode: str) -> None:
        _ = view_mode
        self.title_label.setVisible(True)
        self.title_value.setVisible(True)
        self.preview_label.setMinimumHeight(320)
        self._apply_preview()

    def set_selection_summary(self, text: str) -> None:
        self.selection_summary_label.setText(text)

    def set_record(self, record: WallpaperRecord | None) -> None:
        self._record = record
        if record is None:
            self._clear_preview_movie()
            self.title_value.setText("未选中壁纸")
            self.metadata_value.setText("请从列表或缩略图中选择壁纸。")
            self._preview_source = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("暂无预览")
            self.preview_button.setEnabled(False)
            self.open_folder_button.setEnabled(False)
            self.extract_button.setEnabled(False)
            return

        self.title_value.setText(record.display_title)
        self.metadata_value.setText("\n".join(metadata_lines(record)))
        self._load_preview(record.preview_path)
        has_preview = bool(record.preview_path and os.path.exists(record.preview_path))
        self.preview_button.setEnabled(has_preview)
        self.open_folder_button.setEnabled(True)
        self.extract_button.setEnabled(bool(record.id))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._apply_preview()

    def _load_preview(self, preview_path: str) -> None:
        self._clear_preview_movie()
        if not preview_path or not os.path.exists(preview_path):
            self._preview_source = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("当前项目没有可用的预览图")
            return

        if preview_path.lower().endswith(".gif"):
            movie = QMovie(preview_path)
            if movie.isValid():
                self._preview_source = None
                self._preview_movie = movie
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText("")
                movie.frameChanged.connect(self._apply_preview)
                movie.start()
                self._apply_preview()
                return

        pixmap = load_static_pixmap(preview_path)
        if pixmap.isNull():
            self._preview_source = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("预览图加载失败")
            return

        self._preview_source = pixmap
        self._apply_preview()

    def _apply_preview(self) -> None:
        source_pixmap = self._preview_source
        if self._preview_movie is not None:
            source_pixmap = self._preview_movie.currentPixmap()

        if source_pixmap is None or source_pixmap.isNull():
            return

        target_size = self.preview_label.contentsRect().size()
        if not target_size.isValid():
            target_size = self.preview_label.size()
        bounded_size = target_size.boundedTo(source_pixmap.size())
        if not bounded_size.isValid():
            bounded_size = target_size
        scaled_pixmap = source_pixmap.scaled(
            bounded_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.preview_label.setText("")
        self.preview_label.setPixmap(scaled_pixmap)

    def _clear_preview_movie(self) -> None:
        if self._preview_movie is None:
            return

        self._preview_movie.stop()
        try:
            self._preview_movie.frameChanged.disconnect(self._apply_preview)
        except (RuntimeError, TypeError):
            pass
        self._preview_movie = None

    def _emit_preview_requested(self) -> None:
        if self._record is not None:
            self.preview_requested.emit(self._record.id)

    def _emit_open_folder_requested(self) -> None:
        if self._record is not None:
            self.open_folder_requested.emit(self._record.id)

    def _emit_extract_requested(self) -> None:
        if self._record is not None:
            self.extract_requested.emit(self._record.id)
