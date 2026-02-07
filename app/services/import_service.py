from __future__ import annotations

from openpyxl import load_workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Nomenclature, Service, Unit


class ImportService:
    MODELS = {
        "units": Unit,
        "services": Service,
        "nomenclature": Nomenclature,
    }

    def __init__(self, session: Session):
        self.session = session

    def preview(self, file_path: str, limit: int = 20) -> list[dict]:
        wb = load_workbook(file_path, read_only=True, keep_vba=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(x) if x else "" for x in rows[0]]
        data = []
        for row in rows[1 : 1 + limit]:
            data.append({headers[i]: row[i] for i in range(len(headers))})
        return data

    def import_rows(self, file_path: str, target: str, mapping: dict[str, str]) -> int:
        model = self.MODELS[target]
        wb = load_workbook(file_path, read_only=True, keep_vba=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        headers = [str(x) if x else "" for x in rows[0]]
        count = 0
        for row in rows[1:]:
            payload = {dest: row[headers.index(src)] for src, dest in mapping.items() if src in headers}
            code = payload.get("code")
            if not code:
                continue
            existing = self.session.scalar(select(model).where(model.code == str(code)))
            if existing:
                for k, v in payload.items():
                    setattr(existing, k, v)
            else:
                self.session.add(model(**payload))
            count += 1
        return count
