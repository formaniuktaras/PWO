from __future__ import annotations

from datetime import date

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import select

from app.models.entities import Event, EventItem, EventUnit, Unit


class EventEditorDialog(QDialog):
    def __init__(self, session_factory, event_id: int | None = None):
        super().__init__()
        self.session_factory = session_factory
        self.event_id = event_id
        self.setWindowTitle("Event Editor")

        self.title_edit = QLineEdit()
        self.version_label = QLabel("-")

        self.units_table = QTableWidget(0, 3)
        self.units_table.setHorizontalHeaderLabels(["ID", "Unit", "Primary"])

        self.items_table = QTableWidget(0, 5)
        self.items_table.setHorizontalHeaderLabels(["ID", "Kind", "Object/Nom", "Service", "Qty"])

        self.docs_stub = QLabel("Documents tab (MVP)")
        self.val_stub = QLabel("Valuations tab (MVP)")

        tabs = QTabWidget()
        unit_wrap = QWidget(); uv = QVBoxLayout(unit_wrap); uv.addWidget(self.units_table)
        item_wrap = QWidget(); iv = QVBoxLayout(item_wrap); iv.addWidget(self.items_table)
        tabs.addTab(unit_wrap, "Units")
        tabs.addTab(item_wrap, "Items")
        tabs.addTab(self.docs_stub, "Documents")
        tabs.addTab(self.val_stub, "Valuations")

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)

        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Row version", self.version_label)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(tabs)
        layout.addWidget(save_btn)

        if self.event_id:
            self.load()

    def load(self):
        with self.session_factory() as s:
            e = s.get(Event, self.event_id)
            self.title_edit.setText(e.title)
            self.version_label.setText(str(e.row_version))

            units = s.scalars(select(EventUnit).where(EventUnit.event_id == self.event_id)).all()
            self.units_table.setRowCount(len(units))
            for r, u in enumerate(units):
                unit = s.get(Unit, u.unit_id)
                self.units_table.setItem(r, 0, QTableWidgetItem(str(u.id)))
                self.units_table.setItem(r, 1, QTableWidgetItem(unit.short_name if unit else str(u.unit_id)))
                self.units_table.setItem(r, 2, QTableWidgetItem("Yes" if u.is_primary else "No"))

            items = s.scalars(select(EventItem).where(EventItem.event_id == self.event_id)).all()
            self.items_table.setRowCount(len(items))
            for r, i in enumerate(items):
                self.items_table.setItem(r, 0, QTableWidgetItem(str(i.id)))
                self.items_table.setItem(r, 1, QTableWidgetItem(i.kind.value))
                self.items_table.setItem(r, 2, QTableWidgetItem(str(i.object_id or i.nom_id)))
                self.items_table.setItem(r, 3, QTableWidgetItem(str(i.service_id)))
                self.items_table.setItem(r, 4, QTableWidgetItem(str(i.qty)))

    def save(self):
        with self.session_factory() as s:
            if self.event_id:
                e = s.get(Event, self.event_id)
                loaded_version = int(self.version_label.text())
                if e.row_version != loaded_version:
                    QMessageBox.warning(self, "Conflict", "Event updated by another user. Reload.")
                    return
                e.title = self.title_edit.text().strip()
                e.row_version += 1
            else:
                e = Event(title=self.title_edit.text().strip(), event_date=date.today(), status="draft")
                s.add(e)
            s.commit()
        self.accept()


class EventsTab(QWidget):
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search events")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Date", "Status"])

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load)
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self.add_event)
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_event)

        top = QHBoxLayout()
        top.addWidget(self.search)
        top.addWidget(refresh_btn)
        top.addWidget(add_btn)
        top.addWidget(edit_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.table)
        self.load()

    def load(self):
        with self.session_factory() as s:
            q = select(Event)
            if self.search.text().strip():
                q = q.where(Event.title.ilike(f"%{self.search.text().strip()}%"))
            rows = s.scalars(q.order_by(Event.id.desc())).all()
            self.table.setRowCount(len(rows))
            for r, e in enumerate(rows):
                self.table.setItem(r, 0, QTableWidgetItem(str(e.id)))
                self.table.setItem(r, 1, QTableWidgetItem(e.title))
                self.table.setItem(r, 2, QTableWidgetItem(e.event_date.isoformat()))
                self.table.setItem(r, 3, QTableWidgetItem(e.status))

    def _selected_event_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        return int(self.table.item(row, 0).text())

    def add_event(self):
        dlg = EventEditorDialog(self.session_factory)
        if dlg.exec():
            self.load()

    def edit_event(self):
        event_id = self._selected_event_id()
        if not event_id:
            QMessageBox.information(self, "Info", "Select event")
            return
        dlg = EventEditorDialog(self.session_factory, event_id)
        if dlg.exec():
            self.load()
