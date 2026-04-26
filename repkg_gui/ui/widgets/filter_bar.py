from __future__ import annotations

from typing import Mapping

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QStackedWidget, QWidget

from repkg_gui.domain.entities import FilterState
from repkg_gui.domain.enums import FilterField
from repkg_gui.models.selection_model import FILTER_FIELD_BY_LABEL, FILTER_FIELD_LABELS


class FilterBar(QWidget):
    filter_changed = Signal(object)
    reset_requested = Signal()
    select_all_requested = Signal()
    batch_extract_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._options_by_field: dict[str, tuple[str, ...]] = {
            FilterField.TAGS.value: (),
            FilterField.TYPE.value: (),
        }

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.field_label = QLabel("筛选字段：")
        self.field_combo = QComboBox()
        for field, label in FILTER_FIELD_LABELS.items():
            self.field_combo.addItem(label, field.value)

        self.value_label = QLabel("关键词：")
        self.value_stack = QStackedWidget()
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("输入标题关键字")
        self.value_combo = QComboBox()
        self.value_combo.addItem("")
        self.value_stack.addWidget(self.title_edit)
        self.value_stack.addWidget(self.value_combo)

        self.reset_button = QPushButton("重置筛选")
        self.select_all_button = QPushButton("全选")
        self.batch_extract_button = QPushButton("批量提取")

        layout.addWidget(self.field_label)
        layout.addWidget(self.field_combo)
        layout.addWidget(self.value_label)
        layout.addWidget(self.value_stack, 1)
        layout.addWidget(self.reset_button)
        layout.addWidget(self.select_all_button)
        layout.addWidget(self.batch_extract_button)

        self.field_combo.currentIndexChanged.connect(self._handle_field_changed)
        self.title_edit.textChanged.connect(self._emit_filter_changed)
        self.value_combo.currentTextChanged.connect(self._emit_filter_changed)
        self.reset_button.clicked.connect(self.reset_requested.emit)
        self.select_all_button.clicked.connect(self.select_all_requested.emit)
        self.batch_extract_button.clicked.connect(self.batch_extract_requested.emit)

        self._handle_field_changed()

    def current_field(self) -> FilterField:
        current_label = self.field_combo.currentText()
        return FILTER_FIELD_BY_LABEL.get(current_label, FilterField.TITLE)

    def current_value(self) -> str:
        if self.current_field() is FilterField.TITLE:
            return self.title_edit.text().strip()
        return self.value_combo.currentText().strip()

    def set_filter_options(self, options_by_field: Mapping[str, tuple[str, ...]]) -> None:
        self._options_by_field.update(dict(options_by_field))
        self._rebuild_value_options()

    def set_filter_state(self, filter_state: FilterState) -> None:
        target_index = self.field_combo.findText(FILTER_FIELD_LABELS[filter_state.field])
        if target_index >= 0:
            with QSignalBlocker(self.field_combo):
                self.field_combo.setCurrentIndex(target_index)
        self._rebuild_value_options()

        if filter_state.field is FilterField.TITLE:
            with QSignalBlocker(self.title_edit):
                self.title_edit.setText(filter_state.value)
        else:
            current_index = self.value_combo.findText(filter_state.value)
            if current_index < 0 and filter_state.value:
                self.value_combo.addItem(filter_state.value)
                current_index = self.value_combo.findText(filter_state.value)
            with QSignalBlocker(self.value_combo):
                self.value_combo.setCurrentIndex(max(current_index, 0))

    def set_list_mode(self, is_list_mode: bool) -> None:
        self.select_all_button.setVisible(is_list_mode)
        self.batch_extract_button.setVisible(is_list_mode)

    def _handle_field_changed(self) -> None:
        self._rebuild_value_options(reset_value=True)
        self._emit_filter_changed()

    def _rebuild_value_options(self, reset_value: bool = False) -> None:
        current_field = self.current_field()
        is_title_field = current_field is FilterField.TITLE
        self.value_stack.setCurrentWidget(self.title_edit if is_title_field else self.value_combo)
        self.value_label.setText("关键词：" if is_title_field else "选项：")

        if is_title_field:
            if reset_value:
                with QSignalBlocker(self.title_edit):
                    self.title_edit.clear()
            return

        options = self._options_by_field.get(current_field.value, ())
        current_text = "" if reset_value else self.value_combo.currentText()
        with QSignalBlocker(self.value_combo):
            self.value_combo.clear()
            self.value_combo.addItem("")
            for option in options:
                self.value_combo.addItem(option)
            current_index = self.value_combo.findText(current_text)
            self.value_combo.setCurrentIndex(max(current_index, 0))

    def _emit_filter_changed(self) -> None:
        self.filter_changed.emit(FilterState(field=self.current_field(), value=self.current_value()))
