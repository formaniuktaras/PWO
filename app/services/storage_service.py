from __future__ import annotations

from datetime import date
from pathlib import Path

from app.utils.files import sha256_file


class StorageService:
    def __init__(self, storage_root: str):
        self.root = Path(storage_root)

    def ensure_event_dirs(self, event_id: int) -> Path:
        base = self.root / "events" / str(event_id)
        for part in ["documents", "attachments", "exports"]:
            (base / part).mkdir(parents=True, exist_ok=True)
        return base

    def build_doc_name(
        self, *, doc_date: date, primary_unit_code: str, doc_type: str, doc_no: str, reg_date: date, ext: str
    ) -> str:
        return f"{doc_date.isoformat()}__{primary_unit_code}__{doc_type}__№{doc_no}__reg_{reg_date.isoformat()}.{ext}"

    def relative_to_root(self, p: Path) -> str:
        return str(p.relative_to(self.root))

    def hash(self, p: Path) -> str:
        return sha256_file(p)
