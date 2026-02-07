from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
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

from app.models.entities import AssetObject, DocType, Document, Nomenclature, Service, Unit
from app.services.import_service import ImportService


class DictionariesTab(QWidget):
    MODELS = {
        "Units": (Unit, ["id", "code", "short_name", "full_name"]),
        "Services": (Service, ["id", "code", "name"]),
        "Nomenclature": (Nomenclature, ["id", "code", "name", "unit_measure"]),
        "DocTypes": (DocType, ["id", "code", "name", "extension"]),
    }

    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.selector = QComboBox()
        self.selector.addItems(self.MODELS.keys())
        self.table = QTableWidget(0, 1)
        self.import_btn = QPushButton("Import xlsx/xlsm")
        self.import_btn.clicked.connect(self.import_xlsx)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load)

        top = QHBoxLayout()
        top.addWidget(QLabel("Dictionary:"))
        top.addWidget(self.selector)
        top.addWidget(refresh_btn)
        top.addWidget(self.import_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        self.selector.currentTextChanged.connect(self.load)
        self.load()

    def load(self):
        model, cols = self.MODELS[self.selector.currentText()]
        with self.session_factory() as s:
            rows = s.scalars(select(model).order_by(model.id.desc())).all()
            self.table.setColumnCount(len(cols))
            self.table.setHorizontalHeaderLabels(cols)
            self.table.setRowCount(len(rows))
            for r, obj in enumerate(rows):
                for c, col in enumerate(cols):
                    self.table.setItem(r, c, QTableWidgetItem(str(getattr(obj, col, ""))))

    def import_xlsx(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel", filter="Excel (*.xlsx *.xlsm)")
        if not path:
            return
        target_key = self.selector.currentText().lower()
        target = "units" if target_key == "units" else "services" if target_key == "services" else "nomenclature"
        if target_key == "doctypes":
            QMessageBox.information(self, "Import", "Import for doc types is TODO in MVP.")
            return
        with self.session_factory() as s:
            svc = ImportService(s)
            preview = svc.preview(path)
            if preview:
                QMessageBox.information(self, "Preview", str(preview[:3]))
            mapping = {
                "code": "code",
                "name": "name",
                "short_name": "short_name",
                "full_name": "full_name",
                "unit_measure": "unit_measure",
            }
            count = svc.import_rows(path, target, mapping)
            s.commit()
        QMessageBox.information(self, "Done", f"Imported/updated rows: {count}")
        self.load()


class AssetsTab(QWidget):
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.search = QLineEdit()
        self.search.setPlaceholderText("Inventory/VIN/plate")
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Inv", "VIN", "Plate"])
        btn = QPushButton("Search")
        btn.clicked.connect(self.load)

        top = QHBoxLayout()
        top.addWidget(self.search)
        top.addWidget(btn)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        self.load()

    def load(self):
        with self.session_factory() as s:
            q = select(AssetObject)
            term = self.search.text().strip()
            if term:
                q = q.where(
                    AssetObject.inv_no.ilike(f"%{term}%") | AssetObject.vin.ilike(f"%{term}%") | AssetObject.plate_no.ilike(f"%{term}%")
                )
            rows = s.scalars(q).all()
            self.table.setRowCount(len(rows))
            for r, a in enumerate(rows):
                self.table.setItem(r, 0, QTableWidgetItem(str(a.id)))
                self.table.setItem(r, 1, QTableWidgetItem(a.name))
                self.table.setItem(r, 2, QTableWidgetItem(a.inv_no or ""))
                self.table.setItem(r, 3, QTableWidgetItem(a.vin or ""))
                self.table.setItem(r, 4, QTableWidgetItem(a.plate_no or ""))


class DocumentsTab(QWidget):
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["ID", "Event", "Type", "No", "Path"])
        btn = QPushButton("Refresh")
        btn.clicked.connect(self.load)
        layout = QVBoxLayout(self)
        layout.addWidget(btn)
        layout.addWidget(self.table)
        self.load()

    def load(self):
        with self.session_factory() as s:
            docs = s.scalars(select(Document).order_by(Document.id.desc())).all()
            self.table.setRowCount(len(docs))
            for r, d in enumerate(docs):
                self.table.setItem(r, 0, QTableWidgetItem(str(d.id)))
                self.table.setItem(r, 1, QTableWidgetItem(str(d.event_id)))
                self.table.setItem(r, 2, QTableWidgetItem(str(d.doc_type_id)))
                self.table.setItem(r, 3, QTableWidgetItem(str(d.doc_no or "")))
                self.table.setItem(r, 4, QTableWidgetItem(d.file_path))
