from __future__ import annotations

import getpass

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models.entities import Role, RoleCode, User
from app.services.settings_service import SettingsService


def main() -> None:
    settings = SettingsService(SettingsService.resolve_path())
    db = settings.config.database
    dsn = f"postgresql+psycopg://{db.user}:{db.password}@{db.host}:{db.port}/{db.dbname}"
    engine = create_engine(dsn)
    username = input("Admin username: ").strip()
    password = getpass.getpass("Admin password: ")

    with Session(engine) as s:
        role = s.scalar(select(Role).where(Role.code == RoleCode.ADMIN))
        if not role:
            raise RuntimeError("Roles are missing, run migrations")
        exists = s.scalar(select(User).where(User.username == username))
        if exists:
            exists.password_hash = hash_password(password)
            exists.role_id = role.id
            exists.is_active = True
        else:
            s.add(User(username=username, password_hash=hash_password(password), role_id=role.id, is_active=True))
        s.commit()
    print("Admin user ready")


if __name__ == "__main__":
    main()
