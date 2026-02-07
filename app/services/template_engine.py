from __future__ import annotations

import shutil
from pathlib import Path

from docx import Document as DocxDocument
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.models.entities import DocType, Document, Event, EventUnit, Unit, User
from app.services.audit_service import AuditService
from app.services.storage_service import StorageService


class TemplateEngine:
    def __init__(self, session: Session, storage: StorageService, templates_root: str, user: User):
        self.session = session
        self.storage = storage
        self.templates_root = Path(templates_root)
        self.audit = AuditService(session, user)

    def generate(self, doc_type: DocType, event_id: int, context: dict[str, str]) -> Path:
        event = self.session.get(Event, event_id)
        if not event:
            raise ValueError("Event not found")
        primary = self.session.query(Unit).join(EventUnit, EventUnit.unit_id == Unit.id).filter(
            EventUnit.event_id == event_id, EventUnit.is_primary.is_(True)
        ).first()
        primary_code = primary.code if primary else "MAIN"

        template_file = self.templates_root / f"{doc_type.code}.{doc_type.extension}"
        if not template_file.exists():
            raise FileNotFoundError(f"Template missing: {template_file}")

        event_base = self.storage.ensure_event_dirs(event_id)
        filename = self.storage.build_doc_name(
            doc_date=event.event_date,
            primary_unit_code=primary_code,
            doc_type=doc_type.code,
            doc_no=context.get("DOC_NO", "draft"),
            reg_date=event.event_date,
            ext=doc_type.extension,
        )
        out_file = event_base / "documents" / filename
        shutil.copy2(template_file, out_file)

        ext = doc_type.extension.lower()
        if ext == "docx":
            self._fill_docx(out_file, context)
        elif ext == "xlsx":
            self._fill_xlsx(out_file, context)
        # docm/xlsm copied as-is to preserve macros (TODO: safe substitution)

        rel = self.storage.relative_to_root(out_file)
        doc = Document(
            event_id=event_id,
            doc_type_id=doc_type.id,
            doc_no=context.get("DOC_NO"),
            doc_date=event.event_date,
            reg_date=event.event_date,
            file_path=rel,
            sha256=self.storage.hash(out_file),
        )
        self.session.add(doc)
        self.session.flush()
        self.audit.log("generate", "documents", str(doc.id), f"Generated from template {template_file.name}")
        return out_file

    def _fill_docx(self, path: Path, context: dict[str, str]) -> None:
        d = DocxDocument(path)
        for p in d.paragraphs:
            for key, val in context.items():
                p.text = p.text.replace(f"{{{{{key}}}}}", str(val))
        d.save(path)

    def _fill_xlsx(self, path: Path, context: dict[str, str]) -> None:
        wb = load_workbook(path, keep_vba=True)
        for name in wb.defined_names:
            if name in context:
                defn = wb.defined_names[name]
                for _, cell in defn.destinations:
                    ws = wb[cell.split("!")[0].replace("'", "")]
                    ws[cell.split("!")[1]] = context[name]
        wb.save(path)
