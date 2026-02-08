from __future__ import annotations

import csv
import json
import shutil
import zipfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Document, Event, EventItem, EventUnit, Unit, Valuation, ValuationLink
from app.services.audit_service import AuditService
from app.services.storage_service import StorageService


class ExportService:
    def __init__(self, session: Session, storage: StorageService, user):
        self.session = session
        self.storage = storage
        self.audit = AuditService(session, user)

    def export_event(self, event_id: int, as_zip: bool = True) -> Path:
        event = self.session.get(Event, event_id)
        if not event:
            raise ValueError("Event not found")
        base = self.storage.ensure_event_dirs(event_id)
        export_dir = base / "exports" / f"event_{event_id}"
        if export_dir.exists():
            shutil.rmtree(export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        units = self.session.scalars(select(EventUnit).where(EventUnit.event_id == event_id)).all()
        items = self.session.scalars(select(EventItem).where(EventItem.event_id == event_id)).all()
        docs = self.session.scalars(select(Document).where(Document.event_id == event_id)).all()
        vals = self.session.scalars(select(Valuation).where(Valuation.event_id == event_id)).all()
        val_ids = [v.id for v in vals] or [-1]
        links = self.session.scalars(select(ValuationLink).where(ValuationLink.valuation_id.in_(val_ids))).all()

        metadata = {
            "event": {"id": event.id, "title": event.title, "event_date": event.event_date.isoformat(), "status": event.status},
            "units": [{"id": u.id, "unit_id": u.unit_id, "is_primary": u.is_primary} for u in units],
            "items": [
                {
                    "id": i.id,
                    "kind": i.kind.value,
                    "state": i.state.value if i.state else None,
                    "object_id": i.object_id,
                    "nom_id": i.nom_id,
                    "service_id": i.service_id,
                    "unit_id": i.unit_id,
                    "qty": i.qty,
                }
                for i in items
            ],
            "documents": [{"id": d.id, "doc_type_id": d.doc_type_id, "doc_no": d.doc_no, "file_path": d.file_path} for d in docs],
            "valuations": [
                {
                    "id": v.id,
                    "service_id": v.service_id,
                    "kind": v.kind.value,
                    "value_uah": float(v.value_uah) if v.value_uah is not None else None,
                    "date_effective": v.date_effective.isoformat() if v.date_effective else None,
                    "document_id": v.document_id,
                }
                for v in vals
            ],
            "valuation_links": [{"id": l.id, "valuation_id": l.valuation_id, "event_item_id": l.event_item_id, "applies_qty": l.applies_qty} for l in links],
        }
        with (export_dir / "event.json").open("w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        with (export_dir / "items.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "kind", "state", "object_id", "nom_id", "service_id", "unit_id", "qty"])
            for i in items:
                w.writerow([i.id, i.kind.value, i.state.value if i.state else "", i.object_id, i.nom_id, i.service_id, i.unit_id, i.qty])

        docs_dir = export_dir / "documents"
        docs_dir.mkdir(exist_ok=True)
        for d in docs:
            src = self.storage.root / d.file_path
            if src.exists():
                shutil.copy2(src, docs_dir / src.name)

        self.audit.log("export", "events", str(event_id), "Event package export")

        if as_zip:
            zip_path = base / "exports" / f"event_{event_id}.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for p in export_dir.rglob("*"):
                    if p.is_file():
                        z.write(p, p.relative_to(export_dir))
            return zip_path
        return export_dir
