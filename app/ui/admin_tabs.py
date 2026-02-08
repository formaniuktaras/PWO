from __future__ import annotations

from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from app.auth.security import hash_password
from app.models.entities import Event, Role, RoleCode, User
from app.services.backup_service import BackupService
from app.services.export_service import ExportService
from app.services.settings_service import SettingsService
from app.services.storage_service import StorageService


class AdminUsersTab(QWidget):
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Username", "Role", "Active"])
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.load)
        add = QPushButton("Add user")
        add.clicked.connect(self.add_user)
        top = QHBoxLayout()
        top.addWidget(refresh)
        top.addWidget(add)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        self.load()

    def load(self):
        with self.session_factory() as s:
            users = s.scalars(select(User)).all()
            self.table.setRowCount(len(users))
            for r, u in enumerate(users):
                self.table.setItem(r, 0, QTableWidgetItem(str(u.id)))
                self.table.setItem(r, 1, QTableWidgetItem(u.username))
                self.table.setItem(r, 2, QTableWidgetItem(u.role.code.value))
                self.table.setItem(r, 3, QTableWidgetItem("Yes" if u.is_active else "No"))

    def add_user(self):
        username, ok = QInputDialog.getText(self, "User", "Username")
        if not ok or not username:
            return
        password, ok = QInputDialog.getText(self, "User", "Password")
        if not ok or not password:
            return
        role_value, ok = QInputDialog.getItem(
            self,
            "User",
            "Role",
            [RoleCode.ADMIN.value, RoleCode.OPERATOR.value, RoleCode.VIEWER.value],
            editable=False,
        )
        if not ok:
            return
        selected_role_code = RoleCode(role_value)
        with self.session_factory() as s:
            role = s.scalar(select(Role).where(Role.code == selected_role_code)) or s.scalar(select(Role))
            s.add(User(username=username, password_hash=hash_password(password), role_id=role.id, is_active=True))
            s.commit()
        self.load()


class BackupExportTab(QWidget):
    def __init__(self, session_factory, settings: SettingsService, current_user, schema_version: str):
        super().__init__()
        self.session_factory = session_factory
        self.settings = settings
        self.current_user = current_user
        self.schema_version = schema_version

        self.event_id = QLineEdit()
        export_btn = QPushButton("Export Event")
        export_btn.clicked.connect(self.export_event)
        backup_btn = QPushButton("Create Backup")
        backup_btn.clicked.connect(self.create_backup)

        form = QFormLayout()
        form.addRow("Event ID", self.event_id)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(export_btn)
        layout.addWidget(backup_btn)

    def export_event(self):
        if not self.event_id.text().strip():
            return
        with self.session_factory() as s:
            storage = StorageService(self.settings.config.storage_root)
            p = ExportService(s, storage, self.current_user).export_event(int(self.event_id.text().strip()), as_zip=True)
            s.commit()
            QMessageBox.information(self, "Export", f"Created: {p}")

    def create_backup(self):
        cfg = self.settings.config
        db = cfg.database
        svc = BackupService(
            cfg.pg_dump_path,
            db.host,
            db.port,
            db.dbname,
            db.user,
            db.password,
            cfg.storage_root,
            cfg.backups_root,
            cfg.app_version,
            self.schema_version,
        )
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            p = svc.create_backup()
            QMessageBox.information(self, "Backup", f"Created: {p}")
        except Exception as e:
            QMessageBox.warning(self, "Backup failed", str(e))
        finally:
            QApplication.restoreOverrideCursor()


class SettingsDialog(QWidget):
    def __init__(self, settings: SettingsService):
        super().__init__()
        self.settings = settings
        self.storage = QLineEdit(settings.config.storage_root)
        self.templates = QLineEdit(settings.config.templates_root)
        self.backups = QLineEdit(settings.config.backups_root)
        save = QPushButton("Save")
        save.clicked.connect(self.on_save)
        form = QFormLayout(self)
        form.addRow("Storage root", self.storage)
        form.addRow("Templates root", self.templates)
        form.addRow("Backups root", self.backups)
        form.addRow(save)

    def on_save(self):
        self.settings.config.storage_root = self.storage.text().strip()
        self.settings.config.templates_root = self.templates.text().strip()
        self.settings.config.backups_root = self.backups.text().strip()
        self.settings.save()
        QMessageBox.information(self, "Saved", "Configuration updated")
