from __future__ import annotations

import os

from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QCheckBox,
)

from app_services import (
    DEFAULT_OUTPUT_PATH,
    LOCAL_OUTPUT_MODE,
    MAX_BATCH_EXTRACT_WORKERS,
    SEPARATE_OUTPUT_MODE,
    SHARED_OUTPUT_MODE,
)

from ...app_context import AppContext
from ...controllers.settings_controller import (
    CONFIG_DISPLAY_PATH,
    INFO_DISPLAY_PATH,
    SettingsController,
    THEME_COLOR_LABELS,
)
from ..widgets.steam_path_selector import SteamPathSelector

OPTION_LABELS = {
    "not_convert_tex_to_image": "不转换 TEX",
    "use_wallpaper_name_as_subdir": "按壁纸名创建子目录",
    "copy_project_json_and_preview": "复制 project.json 和预览文件",
    "overwrite_files": "覆盖现有文件",
}


class SettingsPage(QWidget):
    change_steam_path_requested = Signal()

    def __init__(self, context: AppContext):
        super().__init__()
        self.context = context
        self.controller = SettingsController(context)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        root_layout.addWidget(scroll_area)

        content = QWidget()
        root_layout = QVBoxLayout(content)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(12)
        scroll_area.setWidget(content)

        path_group = QGroupBox("Steam 路径")
        path_layout = QVBoxLayout(path_group)
        path_description = QLabel("这里会显示当前的 steam.exe。点击按钮可重新打开统一的路径选择对话框。")
        path_description.setWordWrap(True)
        path_layout.addWidget(path_description)
        self.steam_path_selector = SteamPathSelector(
            label_text="steam.exe 路径：",
            initial_path=context.state.steam_path,
            read_only=True,
            show_buttons=False,
            show_label=False,
        )
        self.change_steam_path_button = QPushButton("重新选择 steam.exe")
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("steam.exe 路径："))
        path_row.addWidget(self.steam_path_selector, 1)
        path_row.addWidget(self.change_steam_path_button)
        path_layout.addLayout(path_row)
        self.path_files_label = QLabel(
            f"配置文件会写入 {CONFIG_DISPLAY_PATH}，扫描后的壁纸索引会写到 {INFO_DISPLAY_PATH}。"
        )
        self.path_files_label.setWordWrap(True)
        path_layout.addWidget(self.path_files_label)
        root_layout.addWidget(path_group)

        option_group = QGroupBox("自定义选项")
        option_layout = QVBoxLayout(option_group)
        option_hint = QLabel("这些选项暂存于会话状态，不会扩大当前 runtime\\config.json 的持久化字段。")
        option_hint.setWordWrap(True)
        option_layout.addWidget(option_hint)
        self.not_convert_checkbox = QCheckBox("不把 TEX 文件转换为图像")
        self.use_title_checkbox = QCheckBox("使用壁纸名作为子目录名称而不是壁纸 ID")
        self.copy_extra_checkbox = QCheckBox("复制 project.json 和预览文件")
        self.overwrite_checkbox = QCheckBox("覆盖所有现有文件")
        for checkbox in (
            self.not_convert_checkbox,
            self.use_title_checkbox,
            self.copy_extra_checkbox,
            self.overwrite_checkbox,
        ):
            option_layout.addWidget(checkbox)
        root_layout.addWidget(option_group)

        output_group = QGroupBox("输出路径及模式")
        output_form = QFormLayout(output_group)
        output_intro = QLabel("先选输出目录，再选输出模式。提取结果是集中放、原地放，还是按壁纸分文件夹，都由这里控制。")
        output_intro.setWordWrap(True)
        output_form.addRow(output_intro)
        output_path_row = QHBoxLayout()
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText(DEFAULT_OUTPUT_PATH)
        self.output_path_browse_button = QPushButton("选择输出文件夹")
        self.open_output_path_button = QPushButton("打开输出文件夹")
        output_path_row.addWidget(self.output_path_edit, 1)
        output_path_row.addWidget(self.output_path_browse_button)
        output_path_row.addWidget(self.open_output_path_button)
        output_form.addRow("输出路径：", output_path_row)
        self.output_path_hint = QLabel()
        self.output_path_hint.setWordWrap(True)
        output_form.addRow("路径说明：", self.output_path_hint)

        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItems([LOCAL_OUTPUT_MODE, SHARED_OUTPUT_MODE, SEPARATE_OUTPUT_MODE])
        output_form.addRow("输出模式：", self.output_mode_combo)

        self.output_mode_description = QLabel()
        self.output_mode_description.setWordWrap(True)
        output_form.addRow("模式说明：", self.output_mode_description)

        self.batch_workers_spin = QSpinBox()
        self.batch_workers_spin.setRange(0, MAX_BATCH_EXTRACT_WORKERS)
        self.batch_workers_spin.setSpecialValueText("自动")
        output_form.addRow("批量提取并发：", self.batch_workers_spin)
        self.batch_workers_description = QLabel()
        self.batch_workers_description.setWordWrap(True)
        output_form.addRow("并发说明：", self.batch_workers_description)
        root_layout.addWidget(output_group)

        theme_group = QGroupBox("主题配色")
        theme_form = QFormLayout(theme_group)
        theme_intro = QLabel("可选择主题预设，也可以单独调整窗口背景、面板背景、强调色和文本颜色。")
        theme_intro.setWordWrap(True)
        theme_form.addRow(theme_intro)
        self.theme_preset_combo = QComboBox()
        for preset, label in self.controller.theme_preset_options():
            self.theme_preset_combo.addItem(label, preset)
        theme_form.addRow("主题预设：", self.theme_preset_combo)
        self.theme_color_buttons: dict[str, QPushButton] = {}
        for color_key, label in THEME_COLOR_LABELS.items():
            button = QPushButton()
            button.clicked.connect(lambda _checked=False, key=color_key: self._choose_theme_color(key))
            self.theme_color_buttons[color_key] = button
            theme_form.addRow(f"{label}：", button)
        root_layout.addWidget(theme_group)

        scope_group = QGroupBox("持久化范围")
        scope_layout = QVBoxLayout(scope_group)
        scope_layout.addWidget(QLabel("以下设置会写入 runtime\\config.json：steam.exe、输出目录、批量提取并发、主题预设、主题配色。"))
        scope_layout.addWidget(
            QLabel(
                "以下设置仅在当前程序运行期间生效：输出模式、TEX 转换、子目录命名、复制附带文件、覆盖开关。"
            )
        )
        root_layout.addWidget(scope_group)

        summary_group = QGroupBox("当前摘要")
        summary_layout = QVBoxLayout(summary_group)
        self.summary_edit = QPlainTextEdit()
        self.summary_edit.setReadOnly(True)
        self.summary_edit.setMinimumHeight(220)
        summary_layout.addWidget(self.summary_edit)
        root_layout.addWidget(summary_group, 1)
        root_layout.addStretch(1)

        self.change_steam_path_button.clicked.connect(self.change_steam_path_requested.emit)
        self.output_path_browse_button.clicked.connect(self._browse_output_path)
        self.open_output_path_button.clicked.connect(self._open_output_path)
        self.output_path_edit.editingFinished.connect(self._persist_output_path)
        self.output_mode_combo.currentTextChanged.connect(self._handle_output_mode_changed)
        self.batch_workers_spin.valueChanged.connect(self.controller.set_batch_extract_workers)
        self.theme_preset_combo.currentIndexChanged.connect(self._handle_theme_preset_changed)
        self.not_convert_checkbox.toggled.connect(
            lambda value: self._set_option("not_convert_tex_to_image", value)
        )
        self.use_title_checkbox.toggled.connect(
            lambda value: self._set_option("use_wallpaper_name_as_subdir", value)
        )
        self.copy_extra_checkbox.toggled.connect(
            lambda value: self._set_option("copy_project_json_and_preview", value)
        )
        self.overwrite_checkbox.toggled.connect(lambda value: self._set_option("overwrite_files", value))

        self.context.config_changed.connect(self.refresh_from_context)
        self.context.session_changed.connect(self.refresh_from_context)
        self.context.steam_path_changed.connect(lambda _: self.refresh_from_context())
        self.refresh_from_context()

    def refresh_from_context(self) -> None:
        state = self.context.state
        with QSignalBlocker(self.output_mode_combo):
            self.output_mode_combo.setCurrentText(state.output_mode)
        with QSignalBlocker(self.batch_workers_spin):
            self.batch_workers_spin.setValue(state.batch_extract_workers)
        preset_index = self.theme_preset_combo.findData(state.config.theme_preset)
        with QSignalBlocker(self.theme_preset_combo):
            self.theme_preset_combo.setCurrentIndex(max(preset_index, 0))
        with QSignalBlocker(self.not_convert_checkbox):
            self.not_convert_checkbox.setChecked(state.not_convert_tex_to_image)
        with QSignalBlocker(self.use_title_checkbox):
            self.use_title_checkbox.setChecked(state.use_wallpaper_name_as_subdir)
        with QSignalBlocker(self.copy_extra_checkbox):
            self.copy_extra_checkbox.setChecked(state.copy_project_json_and_preview)
        with QSignalBlocker(self.overwrite_checkbox):
            self.overwrite_checkbox.setChecked(state.overwrite_files)
        with QSignalBlocker(self.output_path_edit):
            self.output_path_edit.setText(state.output_path)
        self.steam_path_selector.set_path(state.steam_path)
        self.output_mode_description.setText(self.controller.output_mode_description())
        self.output_path_hint.setText(self._build_output_path_hint(state.output_mode))
        self.batch_workers_description.setText(self.controller.batch_workers_description())
        for color_name, color_value in self.controller.theme_color_values().items():
            self._update_theme_button(color_name, color_value)
        self.summary_edit.setPlainText(self.controller.summary_text())

    def _browse_output_path(self) -> None:
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            "选择输出文件夹",
            self.context.state.output_path or "",
        )
        if selected_directory:
            self.output_path_edit.setText(selected_directory)
            self._persist_output_path()

    def _open_output_path(self) -> None:
        output_path = self.output_path_edit.text().strip() or self.context.state.output_path
        if not output_path:
            QMessageBox.warning(self, "打开文件夹失败", "文件夹路径为空。")
            self.context.set_status("打开文件夹失败：文件夹路径为空。")
            return

        normalized_path = os.path.normpath(output_path)
        if not os.path.exists(normalized_path):
            QMessageBox.warning(self, "打开文件夹失败", f"文件夹不存在：{normalized_path}")
            self.context.set_status(f"打开文件夹失败：{normalized_path} 不存在。")
            return

        try:
            os.startfile(normalized_path)
        except OSError as exc:
            QMessageBox.warning(self, "打开文件夹失败", f"无法打开文件夹：{exc}")
            self.context.set_status(f"打开文件夹失败：{exc}")
            return

        self.context.set_status(f"已打开输出文件夹：{normalized_path}")

    def _persist_output_path(self) -> None:
        self.controller.set_output_path(self.output_path_edit.text())

    def _handle_output_mode_changed(self, output_mode: str) -> None:
        self.controller.set_output_mode(output_mode)

    def _set_option(self, option_name: str, value: bool) -> None:
        self.controller.set_option(option_name, value, label=OPTION_LABELS.get(option_name))

    def _handle_theme_preset_changed(self, index: int) -> None:
        preset = self.theme_preset_combo.itemData(index)
        if preset:
            self.controller.set_theme_preset(str(preset))

    def _choose_theme_color(self, color_name: str) -> None:
        current_value = self.controller.theme_color_values().get(color_name, "#FFFFFF")
        selected_color = QColorDialog.getColor(QColor(current_value), self, f"选择{THEME_COLOR_LABELS[color_name]}")
        if selected_color.isValid():
            self.controller.set_theme_color(color_name, selected_color.name().upper())

    def _update_theme_button(self, color_name: str, color_value: str) -> None:
        button = self.theme_color_buttons[color_name]
        contrast = "#111111" if QColor(color_value).lightness() > 160 else "#FFFFFF"
        button.setText(color_value)
        button.setStyleSheet(f"background-color: {color_value}; color: {contrast};")

    def _build_output_path_hint(self, output_mode: str) -> str:
        if output_mode == LOCAL_OUTPUT_MODE:
            return "当前模式会把结果写回壁纸原目录下的 output 子文件夹；上方输出目录只在切换到集中输出模式时使用。"
        return "当前模式会使用上方输出目录作为导出目标；请确保该目录存在并具备写入权限。"
