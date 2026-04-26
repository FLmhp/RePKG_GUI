from __future__ import annotations

from app_services import AppConfig


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    normalized = value.lstrip("#")
    return tuple(int(normalized[index : index + 2], 16) for index in (0, 2, 4))


def _rgb_to_hex(red: int, green: int, blue: int) -> str:
    return f"#{red:02X}{green:02X}{blue:02X}"


def _blend(color_a: str, color_b: str, ratio: float) -> str:
    ratio = max(0.0, min(ratio, 1.0))
    red_a, green_a, blue_a = _hex_to_rgb(color_a)
    red_b, green_b, blue_b = _hex_to_rgb(color_b)
    return _rgb_to_hex(
        int(red_a + (red_b - red_a) * ratio),
        int(green_a + (green_b - green_a) * ratio),
        int(blue_a + (blue_b - blue_a) * ratio),
    )


def _button_text_color(accent: str) -> str:
    red, green, blue = _hex_to_rgb(accent)
    luminance = (red * 299 + green * 587 + blue * 114) / 1000
    return "#111111" if luminance > 160 else "#FFFFFF"


def build_stylesheet(config: AppConfig) -> str:
    background = config.theme_background
    surface = config.theme_surface
    accent = config.theme_accent
    text = config.theme_text
    panel_surface = _blend(surface, background, 0.18)
    pane_surface = _blend(surface, background, 0.1)
    border = _blend(text, surface, 0.75)
    muted = _blend(text, background, 0.55)
    accent_hover = _blend(accent, "#FFFFFF" if _button_text_color(accent) == "#111111" else "#000000", 0.12)
    button_text = _button_text_color(accent)

    return f"""
    QWidget {{
        color: {text};
    }}
    QScrollArea, QListView, QTableView, QPlainTextEdit, QLineEdit, QComboBox, QSpinBox, QMenu {{
        background-color: {surface};
        color: {text};
        border: 1px solid {border};
        border-radius: 6px;
    }}
    QWidget#qt_scrollarea_viewport, QListView::viewport, QTableView::viewport {{
        background-color: {surface};
    }}
    QMainWindow, QDialog, QTabWidget {{
        background-color: {background};
    }}
    QTabWidget::pane {{
        background-color: {pane_surface};
        border: 1px solid {border};
        border-radius: 8px;
    }}
    QGroupBox {{
        background-color: {panel_surface};
        border: 1px solid {border};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        background-color: {background};
        color: {accent};
    }}
    QPushButton, QToolButton {{
        background-color: {accent};
        color: {button_text};
        border: none;
        border-radius: 6px;
        padding: 6px 12px;
    }}
    QPushButton:hover, QToolButton:hover {{
        background-color: {accent_hover};
    }}
    QPushButton:disabled, QToolButton:disabled {{
        background-color: {border};
        color: {muted};
    }}
    QHeaderView::section, QTabBar::tab {{
        background-color: {surface};
        color: {text};
        border: 1px solid {border};
        padding: 6px 12px;
    }}
    QTabBar::tab:selected {{
        background-color: {accent};
        color: {button_text};
    }}
    QLabel {{
        background-color: transparent;
        border: none;
    }}
    """


def apply_theme(app, config: AppConfig) -> None:
    app.setStyleSheet(build_stylesheet(config))
