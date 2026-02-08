from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from app.db.session import SessionLocal, init_engine
from app.services.settings_service import SettingsService
from app.ui.login import LoginWindow
from app.ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    config_path = SettingsService.resolve_path()
    if not config_path.exists():
        example_candidates = [
            config_path.with_name("config.yaml.example"),
            Path(__file__).resolve().parents[2] / "config.yaml.example",
        ]
        example_path = next((candidate for candidate in example_candidates if candidate.exists()), None)
        if example_path:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
            QMessageBox.information(
                None,
                "Config created",
                f"config.yaml was created at {config_path}.\nFill it in and restart the app.",
            )
        else:
            QMessageBox.critical(None, "Config missing", "Create config.yaml from config.yaml.example first.")
        return 1

    settings = SettingsService(config_path)
    init_engine(settings)

    login = LoginWindow(SessionLocal)
    if login.exec() != LoginWindow.Accepted or login.user is None:
        return 0

    window = MainWindow(SessionLocal, settings, login.user)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
