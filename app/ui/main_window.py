from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget
from sqlalchemy import text

from app.ui.admin_tabs import AdminUsersTab, BackupExportTab, SettingsDialog
from app.ui.common_tabs import AssetsTab, DictionariesTab, DocumentsTab
from app.ui.events import EventsTab


class MainWindow(QMainWindow):
    def __init__(self, session_factory, settings, user):
        super().__init__()
        self.setWindowTitle("PWO Desktop")
        self.resize(1200, 800)
        self.session_factory = session_factory
        self.settings = settings
        self.user = user

        tabs = QTabWidget()
        tabs.addTab(EventsTab(session_factory), "Events")
        tabs.addTab(AssetsTab(session_factory), "Assets")
        tabs.addTab(DocumentsTab(session_factory), "Documents")
        tabs.addTab(DictionariesTab(session_factory), "Dictionaries")

        role = user.role.code.value
        schema_version = self._schema_version()
        if role in {"Admin", "Operator"}:
            tabs.addTab(BackupExportTab(session_factory, settings, user, schema_version), "Backup/Export")
        if role == "Admin":
            tabs.addTab(AdminUsersTab(session_factory), "Administration")
            tabs.addTab(SettingsDialog(settings), "Settings")

        self.setCentralWidget(tabs)

    def _schema_version(self) -> str:
        with self.session_factory() as s:
            row = s.execute(text("SELECT version_num FROM alembic_version LIMIT 1")).fetchone()
            return row[0] if row else "unknown"
