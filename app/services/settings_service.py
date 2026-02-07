from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class DBConfig(BaseModel):
    host: str
    port: int = 5432
    dbname: str
    user: str
    password: str


class AppConfig(BaseModel):
    app_version: str = "0.1.0"
    database: DBConfig
    storage_root: str
    templates_root: str
    backups_root: str
    pg_dump_path: str = "pg_dump"


class SettingsService:
    def __init__(self, path: Path):
        self.path = path
        self.config = self._load()

    def _load(self) -> AppConfig:
        with self.path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        return AppConfig.model_validate(payload)

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.config.model_dump(), f, allow_unicode=True, sort_keys=False)
