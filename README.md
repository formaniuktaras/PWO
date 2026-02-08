# PWO (PySide6 + PostgreSQL)

Windows-only desktop MVP for multi-user asset/event workflow with centralized PostgreSQL and shared file storage (UNC path).

## Архітектура (що де лежить)
- `app/services/settings_service.py` — єдине джерело конфігурації (`config.yaml`, optional `PWO_CONFIG`, `PWO_DB_PASSWORD`).
- `app/models/entities.py` — SQLAlchemy models + constraints + optimistic locking (`row_version`).
- `app/ui/` — PySide6 UI (login, events, dictionaries, backup/export).
- `migrations/` — Alembic. `migrations/env.py` читає той самий `config.yaml`, що й застосунок.

## 1) PostgreSQL на робочому ПК (DB server) — для першокласника

### 1.1 Увімкнути доступ по LAN
У `postgresql.conf`:
```ini
listen_addresses = '*'
port = 5432
```

У `pg_hba.conf` додайте LAN-підмережу (приклад 192.168.1.x):
```conf
host    all    all    192.168.1.0/24    scram-sha-256
```

Потім перезапустіть службу PostgreSQL (Services.msc).

### 1.2 Відкрити firewall
На DB-сервері Windows відкрийте TCP 5432 у Windows Defender Firewall (Inbound rule).

### 1.3 Створити користувача/БД
```sql
CREATE USER pwo_user WITH PASSWORD 'change_me';
CREATE DATABASE pwo OWNER pwo_user;
```

## 2) Налаштувати `config.yaml`
```bash
copy config.yaml.example config.yaml
```
Заповніть:
- `database.host` = IP DB-сервера (наприклад `192.168.1.10`)
- `storage_root/templates_root/backups_root` = UNC шляхи (наприклад `\\DB-PC\pwo\storage`)
- `pg_dump_path` = шлях до `pg_dump.exe` (або `pg_dump`, якщо в PATH)

## 3) Встановлення
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 4) Міграції
Alembic використовує той самий config, що app:
```bash
alembic upgrade head
```

За потреби інший config-файл:
```bash
set PWO_CONFIG=D:\pwo\config.yaml
alembic upgrade head
```

## 5) Ініціалізація
```bash
python scripts/init_storage.py
python scripts/seed_admin.py
```

## 6) Запуск
```bash
python -m app.main
```

## 7) MVP сценарії
- login
- events CRUD + units/items/documents/valuations
- residual wizard (`residual_value_statement` + `valuation_links` з partial qty)
- generate template document (docx/xlsx; xlsm keep_vba; docm safe copy)
- import dictionaries from xlsx/xlsm (auto mapping + override)
- export event package (`event.json`, `items.csv`, docs)
- full backup (`pg_dump -Fc` + storage + `manifest.json` з `alembic_revision`)

## 8) Типові помилки
- **`could not connect to server`**: перевірте `listen_addresses`, `pg_hba.conf`, firewall 5432.
- **`password authentication failed`**: перевірте `database.user/password` або `PWO_DB_PASSWORD`.
- **`Template missing`**: перевірте `doc_types.template_path` і доступність UNC.
- **`Conflict: record changed by another user`**: відкрийте подію повторно (optimistic locking).

## 9) Примітки
- SQLite не підтримується.
- Валюта в MVP: UAH.
- Один `event_item` належить рівно одній службі і одному підрозділу.


## 10) Збірка EXE (PyInstaller, Windows, ONEDIR)
```bat
build\build.bat
```
Альтернатива PowerShell:
```powershell
.\build\build.ps1
```

Що робить скрипт:
- створює `.venv` (якщо відсутній);
- встановлює залежності з `requirements.txt`;
- виконує `pyinstaller pwo.spec --clean`;
- гарантує наявність `dist\PWO\config.yaml.example`;
- створює `dist\PWO\config.yaml` (копія example), якщо його нема.

## 11) Розгортання на клієнтських ПК
1. Скопіюйте всю папку `dist\PWO` на ПК користувача.
2. Переконайтесь, що поруч з `PWO.exe` є `config.yaml`.
3. Відредагуйте `config.yaml` (БД, UNC-шляхи, `pg_dump_path`).
4. Запускайте `PWO.exe` (Python на клієнтському ПК не потрібен).

## 12) Налаштування config.yaml поруч з EXE
Логіка пошуку конфігу:
1. `PWO_CONFIG` (абсолютний шлях).
2. frozen/EXE: `config.yaml` у папці поруч з `PWO.exe`.
3. dev-режим: `config.yaml` у корені проєкту (поруч з `config.yaml.example`).
4. fallback: `./config.yaml` (поточна директорія).

Якщо `config.yaml` відсутній при запуску EXE, застосунок автоматично створить його з `config.yaml.example` і попросить заповнити файл.

## 13) pg_dump_path через UNC (рекомендовано)
Для backup можна вказувати UNC шлях до `pg_dump.exe`, наприклад:
```yaml
pg_dump_path: "\\SERVER\PostgreSQL\bin\pg_dump.exe"
```
Сервіс backup додає директорію `pg_dump.exe` у `PATH` перед запуском, щоб коректно знаходились потрібні DLL.

## 14) Типові проблеми EXE
- **`qwindows.dll` missing**: перевірте, що запускаєте саме збірку з `dist\PWO`, а не тільки `PWO.exe`.
- **`VCRUNTIME*.dll` missing**: встановіть Microsoft Visual C++ Redistributable (x64).
- **`pg_dump not found`**: перевірте `pg_dump_path`; для UNC вкажіть повний шлях до `pg_dump.exe`.
- **`config missing`**: переконайтесь, що поруч з `PWO.exe` є `config.yaml.example`; перший старт створює `config.yaml` автоматично.
