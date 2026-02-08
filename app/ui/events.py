from __future__ import annotations

import shutil
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.models.entities import (
    DocType,
    Document,
    Event,
    EventItem,
    EventItemKind,
    EventUnit,
    Nomenclature,
    Service,
    Unit,
    Valuation,
    ValuationKind,
    ValuationLink,
)
from app.services.audit_service import AuditService
from app.services.export_service import ExportService
from app.services.storage_service import StorageService
from app.services.template_engine import TemplateEngine


class ResidualWizardDialog(QDialog):
    def __init__(self, session, event_id: int):
        super().__init__()
        self.session = session
        self.event_id = event_id
        self.setWindowTitle("Residual Wizard")
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Use", "Item ID", "Kind", "Qty"])
        self.service = QComboBox()
        self.doc = QComboBox()
        self.date_effective = QDateEdit()
        self.date_effective.setDate(QDate.currentDate())
        self.value = QLineEdit()
        self.value.setPlaceholderText("UAH (optional)")

        for svc in session.scalars(select(Service).order_by(Service.name)).all():
            self.service.addItem(f"{svc.code} - {svc.name}", svc.id)
        for d in session.scalars(select(Document).where(Document.event_id == event_id).order_by(Document.id.desc())).all():
            self.doc.addItem(f"{d.id}: {d.doc_no or '-'}", d.id)

        load_btn = QPushButton("Load service items")
        load_btn.clicked.connect(self.load_items)
        ok_btn = QPushButton("Create residual valuation")
        ok_btn.clicked.connect(self.accept)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.addRow("Service", self.service)
        form.addRow("Document", self.doc)
        form.addRow("Date effective", self.date_effective)
        form.addRow("Value UAH", self.value)
        layout.addLayout(form)
        layout.addWidget(load_btn)
        layout.addWidget(self.table)
        layout.addWidget(ok_btn)

    def load_items(self):
        items = self.session.scalars(
            select(EventItem).where(EventItem.event_id == self.event_id, EventItem.service_id == self.service.currentData())
        ).all()
        self.table.setRowCount(len(items))
        for r, i in enumerate(items):
            chk = QCheckBox()
            if i.kind == EventItemKind.OBJECT:
                chk.setChecked(True)
            self.table.setCellWidget(r, 0, chk)
            self.table.setItem(r, 1, QTableWidgetItem(str(i.id)))
            self.table.setItem(r, 2, QTableWidgetItem(i.kind.value))
            qty = QTableWidgetItem(str(i.qty if i.kind == EventItemKind.GROUP else 1))
            qty.setFlags(qty.flags() | Qt.ItemIsEditable)
            self.table.setItem(r, 3, qty)

    def build_payload(self):
        links = []
        for r in range(self.table.rowCount()):
            checked = self.table.cellWidget(r, 0).isChecked()
            if not checked:
                continue
            item_id = int(self.table.item(r, 1).text())
            kind = self.table.item(r, 2).text()
            qty = int(self.table.item(r, 3).text() or "0")
            if kind == EventItemKind.OBJECT.value:
                qty = 1
            links.append((item_id, qty))
        raw_value_uah = self.value.text().strip()
        value_uah: Decimal | None = None
        if raw_value_uah:
            normalized_value = raw_value_uah.replace(",", ".")
            try:
                value_uah = Decimal(normalized_value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except (InvalidOperation, ValueError):
                raise ValueError("Value UAH має бути числом")
            if value_uah < 0:
                raise ValueError("Value UAH не може бути від'ємним")
        return {
            "service_id": self.service.currentData(),
            "document_id": self.doc.currentData(),
            "value_uah": value_uah,
            "date_effective": self.date_effective.date().toPython(),
            "links": links,
        }


class EventEditorDialog(QDialog):
    def __init__(self, session_factory, settings, user, event_id: int | None = None):
        super().__init__()
        self.session_factory = session_factory
        self.settings = settings
        self.user = user
        self.event_id = event_id
        self.setWindowTitle("Event Editor")

        self.title_edit = QLineEdit()
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.status_edit = QLineEdit("draft")
        self.version_label = QLabel("-")

        self.units_table = QTableWidget(0, 3)
        self.units_table.setHorizontalHeaderLabels(["ID", "Unit", "Primary"])

        self.items_table = QTableWidget(0, 8)
        self.items_table.setHorizontalHeaderLabels(["ID", "Unit", "Service", "Kind", "Object", "Nomenclature", "Qty", "State"])

        self.docs_table = QTableWidget(0, 5)
        self.docs_table.setHorizontalHeaderLabels(["ID", "Type", "No", "Reg date", "Path"])

        self.val_table = QTableWidget(0, 5)
        self.val_table.setHorizontalHeaderLabels(["ID", "Kind", "Service", "Value", "Links"])

        tabs = QTabWidget()
        tabs.addTab(self._units_tab(), "Units")
        tabs.addTab(self._items_tab(), "Items")
        tabs.addTab(self._docs_tab(), "Documents")
        tabs.addTab(self._vals_tab(), "Valuations")

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        export_btn = QPushButton("Export package")
        export_btn.clicked.connect(self.export_package)

        form = QFormLayout()
        form.addRow("Title", self.title_edit)
        form.addRow("Date", self.date_edit)
        form.addRow("Status", self.status_edit)
        form.addRow("Row version", self.version_label)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(tabs)
        b = QHBoxLayout(); b.addWidget(save_btn); b.addWidget(export_btn)
        layout.addLayout(b)

        if self.event_id:
            self.load()

    def _units_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.addWidget(self.units_table)
        b = QHBoxLayout()
        for text, handler in [("Add", self.add_unit), ("Delete", self.delete_selected_unit), ("Set primary", self.set_primary_unit)]:
            btn = QPushButton(text); btn.clicked.connect(handler); b.addWidget(btn)
        l.addLayout(b)
        return w

    def _items_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.addWidget(self.items_table)
        b = QHBoxLayout()
        for text, handler in [("Add", self.add_item), ("Delete", self.delete_selected_item)]:
            btn = QPushButton(text); btn.clicked.connect(handler); b.addWidget(btn)
        l.addLayout(b)
        return w

    def _docs_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.addWidget(self.docs_table)
        b = QHBoxLayout()
        for text, handler in [("Attach", self.attach_document), ("Generate", self.generate_document)]:
            btn = QPushButton(text); btn.clicked.connect(handler); b.addWidget(btn)
        l.addLayout(b)
        return w

    def _vals_tab(self):
        w = QWidget(); l = QVBoxLayout(w); l.addWidget(self.val_table)
        b = QHBoxLayout()
        add = QPushButton("Add valuation"); add.clicked.connect(self.add_valuation)
        wiz = QPushButton("Residual wizard"); wiz.clicked.connect(self.residual_wizard)
        b.addWidget(add); b.addWidget(wiz)
        l.addLayout(b)
        return w

    def load(self):
        with self.session_factory() as s:
            e = s.get(Event, self.event_id)
            self.title_edit.setText(e.title)
            self.date_edit.setDate(QDate(e.event_date.year, e.event_date.month, e.event_date.day))
            self.status_edit.setText(e.status)
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
                self.items_table.setItem(r, 1, QTableWidgetItem(str(i.unit_id)))
                self.items_table.setItem(r, 2, QTableWidgetItem(str(i.service_id)))
                self.items_table.setItem(r, 3, QTableWidgetItem(i.kind.value))
                self.items_table.setItem(r, 4, QTableWidgetItem(str(i.object_id or "")))
                self.items_table.setItem(r, 5, QTableWidgetItem(str(i.nom_id or "")))
                self.items_table.setItem(r, 6, QTableWidgetItem(str(i.qty)))
                self.items_table.setItem(r, 7, QTableWidgetItem(i.state.value if i.state else ""))

            docs = s.scalars(select(Document).where(Document.event_id == self.event_id)).all()
            self.docs_table.setRowCount(len(docs))
            for r, d in enumerate(docs):
                self.docs_table.setItem(r, 0, QTableWidgetItem(str(d.id)))
                self.docs_table.setItem(r, 1, QTableWidgetItem(str(d.doc_type_id)))
                self.docs_table.setItem(r, 2, QTableWidgetItem(d.doc_no or ""))
                self.docs_table.setItem(r, 3, QTableWidgetItem(d.reg_date.isoformat() if d.reg_date else ""))
                self.docs_table.setItem(r, 4, QTableWidgetItem(d.file_path))

            vals = s.scalars(select(Valuation).where(Valuation.event_id == self.event_id)).all()
            self.val_table.setRowCount(len(vals))
            for r, v in enumerate(vals):
                links = s.scalars(select(ValuationLink).where(ValuationLink.valuation_id == v.id)).all()
                self.val_table.setItem(r, 0, QTableWidgetItem(str(v.id)))
                self.val_table.setItem(r, 1, QTableWidgetItem(v.kind.value))
                self.val_table.setItem(r, 2, QTableWidgetItem(str(v.service_id)))
                self.val_table.setItem(r, 3, QTableWidgetItem(str(v.value_uah or "")))
                self.val_table.setItem(r, 4, QTableWidgetItem(", ".join(f"{x.event_item_id}:{x.applies_qty}" for x in links)))

    def _must_event(self):
        if not self.event_id:
            QMessageBox.warning(self, "Event", "Save event first")
            return False
        return True

    def add_unit(self):
        if not self._must_event():
            return
        with self.session_factory() as s:
            units = s.scalars(select(Unit).order_by(Unit.short_name)).all()
            items = [f"{u.id} - {u.short_name}" for u in units]
            val, ok = QInputDialog.getItem(self, "Unit", "Select", items, editable=False)
            if not ok:
                return
            unit_id = int(val.split(" - ")[0])
            s.add(EventUnit(event_id=self.event_id, unit_id=unit_id, is_primary=False))
            try:
                s.commit()
            except IntegrityError:
                s.rollback()
                QMessageBox.warning(self, "Unit", "Цей підрозділ вже додано до події")
                return
        self.load()

    def delete_selected_unit(self):
        row = self.units_table.currentRow()
        if row < 0:
            return
        with self.session_factory() as s:
            obj = s.get(EventUnit, int(self.units_table.item(row, 0).text()))
            s.delete(obj)
            s.commit()
        self.load()

    def set_primary_unit(self):
        row = self.units_table.currentRow()
        if row < 0:
            return
        with self.session_factory() as s:
            unit = s.get(EventUnit, int(self.units_table.item(row, 0).text()))
            for x in s.scalars(select(EventUnit).where(EventUnit.event_id == self.event_id)).all():
                x.is_primary = x.id == unit.id
            s.commit()
        self.load()

    def add_item(self):
        if not self._must_event():
            return
        dlg = QDialog(self); dlg.setWindowTitle("Add Item")
        unit = QComboBox(); service = QComboBox(); kind = QComboBox(); kind.addItems(["object", "group"])
        object_id = QLineEdit(); nom_id = QLineEdit(); qty = QSpinBox(); qty.setMinimum(1)
        with self.session_factory() as s:
            for eu in s.scalars(select(EventUnit).where(EventUnit.event_id == self.event_id)).all():
                unit.addItem(str(eu.unit_id), eu.unit_id)
            for sv in s.scalars(select(Service).order_by(Service.name)).all():
                service.addItem(f"{sv.code} - {sv.name}", sv.id)
        f = QFormLayout(dlg)
        f.addRow("Unit", unit); f.addRow("Service", service); f.addRow("Kind", kind)
        f.addRow("Object ID", object_id); f.addRow("Nomenclature ID", nom_id); f.addRow("Qty", qty)
        ok = QPushButton("Save"); f.addRow(ok); ok.clicked.connect(dlg.accept)
        if not dlg.exec():
            return
        with self.session_factory() as s:
            data = {
                "event_id": self.event_id,
                "unit_id": unit.currentData(),
                "service_id": service.currentData(),
                "kind": EventItemKind(kind.currentText()),
                "qty": qty.value(),
            }
            if data["kind"] == EventItemKind.OBJECT:
                data["object_id"] = int(object_id.text())
                data["qty"] = 1
            else:
                data["nom_id"] = int(nom_id.text())
                if data["qty"] <= 0:
                    QMessageBox.warning(self, "Validation", "Group qty must be > 0")
                    return
            s.add(EventItem(**data))
            s.commit()
        self.load()

    def delete_selected_item(self):
        row = self.items_table.currentRow()
        if row < 0:
            return
        with self.session_factory() as s:
            s.delete(s.get(EventItem, int(self.items_table.item(row, 0).text())))
            s.commit()
        self.load()

    def attach_document(self):
        if not self._must_event():
            return
        path, _ = QFileDialog.getOpenFileName(self, "Attach", filter="All files (*.*)")
        if not path:
            return
        with self.session_factory() as s:
            doc_type = s.scalar(select(DocType).limit(1))
            if not doc_type:
                QMessageBox.warning(self, "Documents", "Create doc type first")
                return
            storage = StorageService(self.settings.config.storage_root)
            base = storage.ensure_event_dirs(self.event_id) / "documents"
            src = Path(path)
            dst = base / f"{date.today().isoformat()}__attach__{src.name}"
            shutil.copy2(src, dst)
            s.add(Document(event_id=self.event_id, doc_type_id=doc_type.id, file_path=storage.relative_to_root(dst), sha256=storage.hash(dst)))
            s.commit()
        self.load()

    def generate_document(self):
        if not self._must_event():
            return
        with self.session_factory() as s:
            dtypes = s.scalars(select(DocType).order_by(DocType.name)).all()
            if not dtypes:
                QMessageBox.warning(self, "Generate", "No doc types")
                return
            picked, ok = QInputDialog.getItem(self, "Doc type", "Type", [f"{x.id} - {x.name}" for x in dtypes], editable=False)
            if not ok:
                return
            doc_no, ok = QInputDialog.getText(self, "Doc no", "Document number")
            if not ok:
                return
            dt = next(x for x in dtypes if x.id == int(picked.split(" - ")[0]))
            storage = StorageService(self.settings.config.storage_root)
            engine = TemplateEngine(s, storage, self.settings.config.templates_root, self.user)
            engine.generate(dt, self.event_id, {"DOC_NO": doc_no, "EVENT_DATE": self.date_edit.date().toString("yyyy-MM-dd")})
            s.commit()
        self.load()

    def add_valuation(self):
        if not self._must_event():
            return
        with self.session_factory() as s:
            svc = s.scalar(select(Service).limit(1))
            doc = s.scalar(select(Document).where(Document.event_id == self.event_id).limit(1))
            if not svc:
                return
            s.add(Valuation(event_id=self.event_id, service_id=svc.id, kind=ValuationKind.ACCOUNTING, document_id=doc.id if doc else None))
            s.commit()
        self.load()

    def residual_wizard(self):
        if not self._must_event():
            return
        with self.session_factory() as s:
            dlg = ResidualWizardDialog(s, self.event_id)
            if not dlg.exec():
                return
            try:
                payload = dlg.build_payload()
            except ValueError as exc:
                QMessageBox.warning(self, "Residual", str(exc))
                return
            if not payload["document_id"]:
                QMessageBox.warning(self, "Residual", "Document is required")
                return
            val = Valuation(
                event_id=self.event_id,
                service_id=payload["service_id"],
                kind=ValuationKind.RESIDUAL_VALUE_STATEMENT,
                document_id=payload["document_id"],
                value_uah=payload["value_uah"],
                date_effective=payload["date_effective"],
            )
            s.add(val)
            s.flush()
            for item_id, qty in payload["links"]:
                item = s.get(EventItem, item_id)
                if item.kind == EventItemKind.GROUP and qty > item.qty:
                    QMessageBox.warning(self, "Residual", f"Item {item_id}: applies_qty > qty")
                    s.rollback()
                    return
                s.add(ValuationLink(valuation_id=val.id, event_item_id=item_id, applies_qty=1 if item.kind == EventItemKind.OBJECT else qty))
            s.commit()
        self.load()

    def export_package(self):
        if not self._must_event():
            return
        with self.session_factory() as s:
            path = ExportService(s, StorageService(self.settings.config.storage_root), self.user).export_event(self.event_id, as_zip=True)
            s.commit()
            QMessageBox.information(self, "Export", f"Created {path}")

    def save(self):
        with self.session_factory() as s:
            audit = AuditService(s, self.user)
            if self.event_id:
                e = s.get(Event, self.event_id)
                loaded_version = int(self.version_label.text())
                if e.row_version != loaded_version:
                    if QMessageBox.question(self, "Conflict", "Запис був змінений іншим користувачем. Перезавантажити?"):
                        self.load()
                    return
                before = {"title": e.title, "status": e.status}
                e.title = self.title_edit.text().strip()
                e.event_date = self.date_edit.date().toPython()
                e.status = self.status_edit.text().strip() or "draft"
                audit.log("update", "events", str(e.id), diff={"before": before, "after": {"title": e.title, "status": e.status}})
            else:
                e = Event(title=self.title_edit.text().strip(), event_date=self.date_edit.date().toPython(), status=self.status_edit.text().strip() or "draft")
                s.add(e)
                s.flush()
                self.event_id = e.id
                audit.log("create", "events", str(e.id), details=e.title)
            try:
                s.commit()
            except StaleDataError:
                QMessageBox.warning(self, "Conflict", "Запис був змінений іншим користувачем. Перезавантажити?")
                s.rollback()
                return
        self.accept()


class EventsTab(QWidget):
    def __init__(self, session_factory, settings, user):
        super().__init__()
        self.session_factory = session_factory
        self.settings = settings
        self.user = user

        self.search = QLineEdit(); self.search.setPlaceholderText("Search events")
        self.status_filter = QLineEdit(); self.status_filter.setPlaceholderText("Status")
        self.unit_filter = QLineEdit(); self.unit_filter.setPlaceholderText("Unit ID")
        self.date_from = QDateEdit(); self.date_to = QDateEdit(); self.date_from.setDate(QDate(2000, 1, 1)); self.date_to.setDate(QDate.currentDate())

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Title", "Date", "Status"])

        refresh_btn = QPushButton("Refresh"); refresh_btn.clicked.connect(self.load)
        add_btn = QPushButton("Add"); add_btn.clicked.connect(self.add_event)
        edit_btn = QPushButton("Edit"); edit_btn.clicked.connect(self.edit_event)
        del_btn = QPushButton("Delete"); del_btn.clicked.connect(self.delete_event)

        top = QGridLayout()
        top.addWidget(self.search, 0, 0)
        top.addWidget(self.status_filter, 0, 1)
        top.addWidget(self.unit_filter, 0, 2)
        top.addWidget(self.date_from, 1, 0)
        top.addWidget(self.date_to, 1, 1)
        top.addWidget(refresh_btn, 1, 2)
        top.addWidget(add_btn, 0, 3); top.addWidget(edit_btn, 0, 4); top.addWidget(del_btn, 0, 5)

        layout = QVBoxLayout(self); layout.addLayout(top); layout.addWidget(self.table)
        self.load()

    def load(self):
        with self.session_factory() as s:
            q = select(Event)
            if self.search.text().strip():
                q = q.where(Event.title.ilike(f"%{self.search.text().strip()}%"))
            if self.status_filter.text().strip():
                q = q.where(Event.status.ilike(f"%{self.status_filter.text().strip()}%"))
            q = q.where(Event.event_date >= self.date_from.date().toPython(), Event.event_date <= self.date_to.date().toPython())
            if self.unit_filter.text().strip().isdigit():
                q = q.join(EventUnit, EventUnit.event_id == Event.id).where(EventUnit.unit_id == int(self.unit_filter.text().strip()))
            rows = s.scalars(q.order_by(Event.id.desc())).all()
            self.table.setRowCount(len(rows))
            for r, e in enumerate(rows):
                self.table.setItem(r, 0, QTableWidgetItem(str(e.id)))
                self.table.setItem(r, 1, QTableWidgetItem(e.title))
                self.table.setItem(r, 2, QTableWidgetItem(e.event_date.isoformat()))
                self.table.setItem(r, 3, QTableWidgetItem(e.status))

    def _selected_event_id(self) -> int | None:
        row = self.table.currentRow()
        return int(self.table.item(row, 0).text()) if row >= 0 else None

    def add_event(self):
        dlg = EventEditorDialog(self.session_factory, self.settings, self.user)
        if dlg.exec():
            self.load()

    def edit_event(self):
        event_id = self._selected_event_id()
        if not event_id:
            QMessageBox.information(self, "Info", "Select event")
            return
        dlg = EventEditorDialog(self.session_factory, self.settings, self.user, event_id)
        if dlg.exec():
            self.load()

    def delete_event(self):
        if self.user.role.code.value != "Admin":
            QMessageBox.warning(self, "Denied", "Delete is admin-only")
            return
        event_id = self._selected_event_id()
        if not event_id:
            return
        with self.session_factory() as s:
            s.delete(s.get(Event, event_id))
            AuditService(s, self.user).log("delete", "events", str(event_id))
            s.commit()
        self.load()
