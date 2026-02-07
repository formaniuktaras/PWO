from __future__ import annotations

from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QMessageBox, QPushButton, QVBoxLayout

from app.auth.service import AuthService


class LoginWindow(QDialog):
    def __init__(self, session_factory):
        super().__init__()
        self.setWindowTitle("Login")
        self.user = None
        self._session_factory = session_factory

        self.username = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        btn = QPushButton("Sign in")
        btn.clicked.connect(self.on_login)

        form = QFormLayout()
        form.addRow("Username", self.username)
        form.addRow("Password", self.password)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btn)

    def on_login(self) -> None:
        with self._session_factory() as s:
            user = AuthService(s).authenticate(self.username.text().strip(), self.password.text())
            if not user:
                QMessageBox.warning(self, "Error", "Invalid credentials")
                return
            self.user = user
            self.accept()
