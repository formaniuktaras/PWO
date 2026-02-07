from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Document, Event, EventItem
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

        with (export_dir / "event.json").open("w", encoding="utf-8") as f:
            json.dump({"id": event.id, "title": event.title, "event_date": event.event_date.isoformat()}, f, ensure_ascii=False, indent=2)

        wb = Workbook()
        ws = wb.active
        ws.append(["id", "kind", "object_id", "nom_id", "service_id", "unit_id", "qty"])
        items = self.session.scalars(select(EventItem).where(EventItem.event_id == event_id)).all()
        for i in items:
            ws.append([i.id, i.kind.value, i.object_id, i.nom_id, i.service_id, i.unit_id, i.qty])
        wb.save(export_dir / "items.xlsx")

        docs_dir = export_dir / "documents"
        docs_dir.mkdir(exist_ok=True)
        for d in self.session.scalars(select(Document).where(Document.event_id == event_id)).all():
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
