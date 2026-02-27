from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml
from pydantic import BaseModel
from sqlalchemy import URL


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
        env_path = os.getenv("PWO_CONFIG")
        if env_path:
            resolved = Path(env_path).expanduser()
            return resolved if resolved.is_absolute() else resolved.resolve()

        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent / default

        project_root = Path(__file__).resolve().parents[2]
        dev_path = project_root / default
        if (project_root / "config.yaml.example").exists():
            return dev_path

        return Path.cwd() / default

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
        return URL.create(
            drivername=driver,
            username=db.user,
            password=password,
            host=db.host,
            port=db.port,
            database=db.dbname,
        ).render_as_string(hide_password=not with_password)
