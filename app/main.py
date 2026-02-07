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
    config_path = Path("config.yaml")
    if not config_path.exists():
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
