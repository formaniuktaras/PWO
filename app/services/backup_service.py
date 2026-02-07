from __future__ import annotations

import json
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from app.utils.files import sha256_file


class BackupService:
    def __init__(self, pg_dump_path: str, db_dsn: str, storage_root: str, backups_root: str, app_version: str, schema_version: str):
        self.pg_dump_path = pg_dump_path
        self.db_dsn = db_dsn
        self.storage_root = Path(storage_root)
        self.backups_root = Path(backups_root)
        self.app_version = app_version
        self.schema_version = schema_version

    def create_backup(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        work = self.backups_root / f"backup_{ts}"
        work.mkdir(parents=True, exist_ok=True)
        dump_file = work / "database.dump"
        subprocess.run([self.pg_dump_path, self.db_dsn, "-Fc", "-f", str(dump_file)], check=True)

        storage_copy = work / "storage"
        shutil.copytree(self.storage_root, storage_copy)

        files = [p for p in work.rglob("*") if p.is_file()]
        manifest = {
            "created_at": datetime.now().isoformat(),
            "app_version": self.app_version,
            "schema_version": self.schema_version,
            "files": [{"path": str(p.relative_to(work)), "sha256": sha256_file(p)} for p in files],
        }
        (work / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        out_zip = self.backups_root / f"backup_{ts}.zip"
        with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in work.rglob("*"):
                if p.is_file():
                    z.write(p, p.relative_to(work))
        shutil.rmtree(work)
        return out_zip
