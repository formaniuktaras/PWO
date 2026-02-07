# PWO (PySide6 + PostgreSQL)

Windows-only desktop MVP for multi-user asset/event workflow with centralized PostgreSQL and shared file storage (UNC path).

## Stack
- Python 3.12+
- PySide6
- SQLAlchemy 2.x + Alembic
- PostgreSQL (psycopg)
- passlib[argon2]
- openpyxl + python-docx

## Project structure
```
app/
  auth/
  db/
  models/
  services/
  ui/
  utils/
migrations/
scripts/
config.yaml.example
requirements.txt
```

## 1) PostgreSQL setup
Example (locally):
```sql
CREATE USER pwo_user WITH PASSWORD 'change_me';
CREATE DATABASE pwo OWNER pwo_user;
```

## 2) Setup config
```bash
copy config.yaml.example config.yaml
```
Edit `config.yaml`:
- database connection params
- `storage_root`, `templates_root`, `backups_root` (can be UNC paths)
- optional `pg_dump_path`

## 3) Install deps
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4) Initialize DB + storage
```bash
alembic upgrade head
python scripts/init_storage.py
python scripts/seed_admin.py
```

## 5) Run app
```bash
python -m app.main
```

## Features in this MVP
- Login/password auth + roles (Admin/Operator/Viewer)
- RBAC-based tabs in UI
- Core schema: users/roles, units/services/nomenclature, assets, events(+units/items), docs, valuations(+links), audit log
- Partial unique indexes for `asset_objects.inv_no` and `asset_objects.vin` if value is set
- Event row-version optimistic locking in event editor
- Template generation service (docx/xlsx substitution, docm/xlsm safe copy)
- Dictionary import from xlsx/xlsm (preview + upsert)
- Event package export (json + xlsx + files)
- Backup service (`pg_dump` + storage copy + manifest checksums)

## Notes / TODO in MVP
- Rich event card CRUD for units/items/documents/valuations is intentionally minimal and extendable.
- docm/xlsm in template engine are copied without macro-breaking transforms (safe default).
- Optional Office COM PDF export interface is not wired yet (planned extension with pywin32).
