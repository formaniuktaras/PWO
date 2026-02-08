from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from app.utils.files import sha256_file


class BackupService:
    def __init__(
        self,
        pg_dump_path: str,
        db_host: str,
        db_port: int,
        db_name: str,
        db_user: str,
        db_password: str,
        storage_root: str,
        backups_root: str,
        app_version: str,
        alembic_revision: str,
    ):
        self.pg_dump_path = pg_dump_path
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.storage_root = Path(storage_root)
        self.backups_root = Path(backups_root)
        self.app_version = app_version
        self.alembic_revision = alembic_revision

    def create_backup(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        work = self.backups_root / f"backup_{ts}"
        work.mkdir(parents=True, exist_ok=True)
        dump_file = work / "database.dump"

        env = os.environ.copy()
        env["PGPASSWORD"] = self.db_password
        env["PATH"] = f"{Path(self.pg_dump_path).parent};{env.get('PATH', '')}"
        cmd = [
            self.pg_dump_path,
            "-Fc",
            "-f",
            str(dump_file),
            "-h",
            self.db_host,
            "-p",
            str(self.db_port),
            "-U",
            self.db_user,
            self.db_name,
        ]
        subprocess.run(cmd, check=True, env=env)

        storage_copy = work / "storage"
        shutil.copytree(self.storage_root, storage_copy)

        files = [p for p in work.rglob("*") if p.is_file()]
        manifest = {
            "timestamp": datetime.now().isoformat(),
            "app_version": self.app_version,
            "alembic_revision": self.alembic_revision,
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
