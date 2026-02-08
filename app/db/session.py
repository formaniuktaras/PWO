from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.services.settings_service import SettingsService

engine = None
SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False)


def init_engine(settings: SettingsService) -> None:
    global engine
    engine = create_engine(settings.sqlalchemy_dsn(), pool_pre_ping=True)
    SessionLocal.configure(bind=engine)
