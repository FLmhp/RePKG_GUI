from __future__ import annotations

import sys
from collections.abc import Sequence

from app_services import ensure_config_file, load_config


def main(argv: Sequence[str] | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
    except ImportError as exc:
        print("PySide6 is required to launch the new UI shell.", file=sys.stderr)
        print(f"Import error: {exc}", file=sys.stderr)
        return 1

    app = QApplication.instance()
    if app is None:
        app = QApplication(list(argv) if argv is not None else sys.argv)

    app.setApplicationName("RePKG_GUI")
    app.setOrganizationName("FLmhp")

    ensure_config_file()
    context = _build_context()
    from .theme import apply_theme

    from .ui.dialogs.steam_path_dialog import SteamPathDialog
    from .ui.main_window import MainWindow

    from .controllers.extraction_controller import ExtractionController

    apply_theme(app, context.state.config)
    context.config_changed.connect(lambda: apply_theme(app, context.state.config))

    extraction_controller = ExtractionController(context)
    window = MainWindow(context, extraction_controller=extraction_controller)

    if not context.has_valid_steam_path():
        context.set_status("未检测到有效的 steam.exe 路径，请先完成设置。")
        dialog = SteamPathDialog(context, parent=window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return 0
    else:
        context.set_status("已读取配置，主界面已准备就绪。后续扫描流程可在此基础上接入。")

    window.show()
    window.raise_()
    window.activateWindow()

    return app.exec()


def _build_context():
    from .app_context import AppContext

    return AppContext.from_config(load_config())
