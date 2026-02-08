from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel


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

    @staticmethod
    def resolve_path(default: str = "config.yaml") -> Path:
        return Path(os.getenv("PWO_CONFIG", default))

    def _load(self) -> AppConfig:
        with self.path.open("r", encoding="utf-8") as f:
            payload = yaml.safe_load(f) or {}
        cfg = AppConfig.model_validate(payload)
        env_password = os.getenv("PWO_DB_PASSWORD")
        if env_password:
            cfg.database.password = env_password
        return cfg

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(self.config.model_dump(), f, allow_unicode=True, sort_keys=False)

    def sqlalchemy_dsn(self, *, driver: str = "postgresql+psycopg", with_password: bool = True) -> str:
        db = self.config.database
        password = db.password if with_password else "***"
        return f"{driver}://{db.user}:{password}@{db.host}:{db.port}/{db.dbname}"
