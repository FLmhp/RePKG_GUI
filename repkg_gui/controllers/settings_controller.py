from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from app_services import (
    CONFIG_FILE,
    CUSTOM_THEME_PRESET,
    DEFAULT_OUTPUT_PATH,
    INFO_CSV_FILE,
    LOCAL_OUTPUT_MODE,
    PROJECT_ROOT,
    REPKG_EXECUTABLE,
    RESOURCE_ROOT,
    SEPARATE_OUTPUT_MODE,
    SHARED_OUTPUT_MODE,
    THEME_COLOR_KEYS,
    get_auto_batch_extract_workers,
    resolve_batch_extract_workers,
)

from ..app_metadata import (
    ABOUT_IMAGE_URL,
    APP_AUTHOR,
    APP_AUTHOR_URL,
    APP_VERSION,
    REPKG_AUTHOR,
    REPKG_PROJECT_URL,
    REPKG_VERSION,
)
from ..state.session_state import SessionState

ABOUT_IMAGE_PATH = os.path.join(RESOURCE_ROOT, "nekomusume.png")
CONFIG_DISPLAY_PATH = os.path.relpath(CONFIG_FILE, PROJECT_ROOT)
INFO_DISPLAY_PATH = os.path.relpath(INFO_CSV_FILE, PROJECT_ROOT)
REPKG_DISPLAY_PATH = os.path.relpath(REPKG_EXECUTABLE, PROJECT_ROOT)
RUNTIME_DIR_DISPLAY = os.path.relpath(os.path.dirname(CONFIG_FILE), PROJECT_ROOT)
THEME_PRESET_LABELS = {
    "light": "浅色",
    "dark": "深色",
    "mint": "薄荷",
    "sunset": "落日",
    CUSTOM_THEME_PRESET: "自定义",
}
THEME_COLOR_LABELS = {
    "theme_background": "窗口背景",
    "theme_surface": "面板背景",
    "theme_accent": "强调色",
    "theme_text": "文本颜色",
}


class SettingsContext(Protocol):
    state: SessionState

    def set_batch_extract_workers(self, workers: int) -> None: ...

    def set_option(self, option_name: str, value: bool) -> None: ...

    def set_output_mode(self, output_mode: str) -> None: ...

    def set_output_path(self, output_path: str) -> None: ...

    def set_theme_preset(self, preset: str) -> None: ...

    def set_theme_color(self, color_name: str, color_value: str) -> None: ...

    def set_status(self, message: str) -> None: ...


@dataclass(frozen=True, slots=True)
class HelpSection:
    title: str
    lines: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AboutMetadata:
    app_version: str
    app_author: str
    app_author_url: str
    repkg_version: str
    repkg_author: str
    repkg_project_url: str
    support_image_path: str
    support_image_url: str


@dataclass(slots=True, weakref_slot=True)
class SettingsController:
    context: SettingsContext

    def summary_text(self) -> str:
        return build_settings_summary(self.context.state)

    def output_mode_description(self, output_mode: str | None = None) -> str:
        return get_output_mode_description(output_mode or self.context.state.output_mode)

    def batch_workers_description(self, configured_workers: int | None = None) -> str:
        workers = self.context.state.batch_extract_workers if configured_workers is None else configured_workers
        return get_batch_extract_workers_description(workers)

    def set_batch_extract_workers(self, workers: int) -> None:
        self.context.set_batch_extract_workers(workers)

    def set_option(self, option_name: str, value: bool, label: str | None = None) -> None:
        self.context.set_option(option_name, value)
        if label:
            action_text = "已启用" if value else "已关闭"
            self.context.set_status(f"{label}：{action_text}。")

    def set_output_mode(self, output_mode: str) -> None:
        self.context.set_output_mode(output_mode)

    def set_output_path(self, output_path: str) -> None:
        self.context.set_output_path(output_path)

    def theme_preset_options(self) -> tuple[tuple[str, str], ...]:
        ordered_presets = ("light", "dark", "mint", "sunset", CUSTOM_THEME_PRESET)
        return tuple((preset, THEME_PRESET_LABELS[preset]) for preset in ordered_presets)

    def theme_label(self, preset: str) -> str:
        return THEME_PRESET_LABELS.get(preset, preset)

    def theme_color_values(self) -> dict[str, str]:
        config = self.context.state.config
        return {key: getattr(config, key) for key in THEME_COLOR_KEYS}

    def set_theme_preset(self, preset: str) -> None:
        self.context.set_theme_preset(preset)
        self.context.set_status(f"已切换主题预设：{self.theme_label(self.context.state.config.theme_preset)}")

    def set_theme_color(self, color_name: str, color_value: str) -> None:
        self.context.set_theme_color(color_name, color_value)
        self.context.set_status(f"{THEME_COLOR_LABELS.get(color_name, color_name)} 已更新为 {color_value}")


def get_output_mode_description(mode: str) -> str:
    descriptions = {
        LOCAL_OUTPUT_MODE: "提取结果直接放到壁纸原目录下的 output 文件夹里。",
        SHARED_OUTPUT_MODE: "所有提取结果都放到同一个目录里。",
        SEPARATE_OUTPUT_MODE: "在目标目录下按壁纸分开建文件夹，批量导出更清楚。",
    }
    return descriptions.get(mode, "当前输出模式暂时没有说明。")


def format_batch_extract_workers_display(configured_workers: int) -> str:
    resolved_workers = resolve_batch_extract_workers(configured_workers)
    if configured_workers <= 0:
        return f"自动（当前 {resolved_workers} 线程）"
    return f"{resolved_workers} 线程"


def get_batch_extract_workers_description(configured_workers: int) -> str:
    resolved_workers = resolve_batch_extract_workers(configured_workers)
    if configured_workers <= 0:
        return f"当前为自动模式，会按 CPU 核心数决定并发数，当前实际使用 {resolved_workers} 线程。"
    return f"当前手动设置为 {resolved_workers} 线程。填 0 可切回自动模式。"


def build_settings_summary(state: SessionState) -> str:
    steam_display = state.steam_path or "还没设置"
    output_display = state.output_path or DEFAULT_OUTPUT_PATH
    return "\n".join(
        [
            f"steam.exe：{steam_display}",
            f"输出模式：{state.output_mode}",
            f"输出目录：{output_display}",
            f"批量提取并发：{format_batch_extract_workers_display(state.batch_extract_workers)}",
            f"主题预设：{THEME_PRESET_LABELS.get(state.config.theme_preset, state.config.theme_preset)}",
            f"主题配色：背景 {state.config.theme_background} / 面板 {state.config.theme_surface} / 强调 {state.config.theme_accent} / 文本 {state.config.theme_text}",
            f"配置文件：{CONFIG_DISPLAY_PATH}",
            f"壁纸索引：{INFO_DISPLAY_PATH}",
            "持久化设置：steam.exe / 输出目录 / 批量提取并发 / 主题预设 / 主题配色",
            "当前会话选项：",
            f"- 不转换 TEX：{'是' if state.not_convert_tex_to_image else '否'}",
            f"- 用壁纸名建子目录：{'是' if state.use_wallpaper_name_as_subdir else '否'}",
            f"- 复制 project.json / 预览：{'是' if state.copy_project_json_and_preview else '否'}",
            f"- 覆盖旧文件：{'是' if state.overwrite_files else '否'}",
        ]
    )


def build_help_sections() -> tuple[HelpSection, ...]:
    auto_workers = get_auto_batch_extract_workers()
    return (
        HelpSection(
            title="快速开始",
            lines=(
                "1. 首次启动时，请先在设置页确认 steam.exe 路径。",
                f"2. 路径确认后，程序会扫描 Wallpaper Engine 创意工坊目录并生成 {INFO_DISPLAY_PATH}。",
                "3. 扫描完成后，就能在列表模式或缩略图模式里浏览、筛选和预览壁纸。",
                "4. 提取前看一下输出模式、输出目录和自定义选项。",
            ),
        ),
        HelpSection(
            title="常见操作",
            lines=(
                "1. 顶部“刷新数据”会重新扫一遍本地 Workshop，不用重启。",
                "2. 列表区支持筛选、重置筛选、全选和批量提取。",
                "3. 列表区会显示类型、可见性这些必要信息；右键列表项可以看大图。",
                "4. 批量提取会在后台并发执行，窗口底部状态栏会显示提取状态。",
            ),
        ),
        HelpSection(
            title="设置页说明",
            lines=(
                "1. steam.exe 路径会决定从哪里找本地 Workshop 文件。",
                f"2. “{LOCAL_OUTPUT_MODE}”适合就地导出；“{SHARED_OUTPUT_MODE}”适合集中整理；“{SEPARATE_OUTPUT_MODE}”适合批量分项目保存。",
                "3. 批量提取并发数填 0 表示自动，默认会按 CPU 核心数决定，当前自动值会落在保守范围内。",
                "4. 自定义选项会影响下一次提取，比如是否转换 TEX、复制附带文件、覆盖旧文件。",
                "5. 页面下方的摘要会显示当前路径、输出模式、并发数和配置文件位置。",
            ),
        ),
        HelpSection(
            title="文件位置",
            lines=(
                f"- 运行配置：{CONFIG_DISPLAY_PATH}",
                f"- 壁纸索引：{INFO_DISPLAY_PATH}",
                f"- 日志目录：{RUNTIME_DIR_DISPLAY}",
                f"- 提取工具：{REPKG_DISPLAY_PATH}（基于 {REPKG_VERSION}）",
                f"- 自动并发参考值：当前约 {auto_workers} 线程",
            ),
        ),
    )


def load_about_metadata() -> AboutMetadata:
    return AboutMetadata(
        app_version=APP_VERSION,
        app_author=APP_AUTHOR,
        app_author_url=APP_AUTHOR_URL,
        repkg_version=REPKG_VERSION,
        repkg_author=REPKG_AUTHOR,
        repkg_project_url=REPKG_PROJECT_URL,
        support_image_path=ABOUT_IMAGE_PATH,
        support_image_url=ABOUT_IMAGE_URL,
    )
