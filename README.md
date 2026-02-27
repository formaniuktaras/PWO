# PWO — Windows desktop MVP (PySide6 + PostgreSQL + Alembic)

PWO — це багатокористувацький desktop-застосунок для обліку подій/активів і формування документів, який працює на Windows, використовує PostgreSQL як централізовану БД та спільне файлове сховище (локальне або UNC).

## Ключові можливості
- Авторизація користувачів із ролями (`Admin`, `Operator`, `Viewer`).
- Робота з подіями, об’єктами, групами, документами та оцінками.
- Імпорт довідників (xlsx/xlsm), експорт пакетів подій.
- Резервне копіювання (БД + файли) через `pg_dump`.
- Збірка standalone EXE (PyInstaller, onedir).

---

## Архітектура та структура проєкту

```text
app/
  auth/                  # security, auth service
  db/                    # ініціалізація SQLAlchemy engine/session
  models/                # SQLAlchemy-моделі та enum-и
  services/              # бізнес/інфра сервіси (settings, backup, storage...)
  ui/                    # PySide6 UI
  main.py                # точка входу desktop app

migrations/
  env.py                 # Alembic env (читає той самий config.yaml)
  versions/              # ревізії БД

scripts/
  init_storage.py        # створення storage/templates/backups директорій
  seed_admin.py          # створення/оновлення admin-користувача

build/
  build.bat / build.ps1  # збірка EXE

config.yaml.example      # приклад конфігу
README.md                # цей документ
```

---

## Вимоги

### ОС і софт
- Windows 10/11 або Windows Server (для DB-сервера).
- Python 3.11+ (рекомендовано).
- PostgreSQL 14+ (рекомендовано).
- PowerShell 5.1+ або PowerShell 7+.

### Мережа
- Клієнтські ПК мають бачити PostgreSQL-хост по TCP 5432.
- Для мережевих каталогів (`\\server\share\...`) потрібні права читання/запису.

### UNC/Storage
- Шляхи `storage_root`, `templates_root`, `backups_root` мають існувати або бути доступними для створення.
- Користувач, під яким запускається PWO/EXE, повинен мати доступ до цих шляхів.

---

## Quick Start (чистий запуск з нуля, Windows PowerShell)

> Усі команди нижче — PowerShell-safe.

### 1) Клон/перехід у репозиторій
```powershell
cd D:\work\PWO
```

### 2) Створити venv і встановити залежності
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
```

### 3) Створити `config.yaml`
```powershell
Copy-Item .\config.yaml.example .\config.yaml
notepad .\config.yaml
```

### 4) Підготувати PostgreSQL (на DB-сервері)
```sql
CREATE USER pwo_user WITH PASSWORD 'ChangeMe_Strong!';
CREATE DATABASE pwo OWNER pwo_user;
```

### 5) Застосувати міграції
```powershell
py -m alembic upgrade head
```

### 6) Ініціалізувати файлове сховище
```powershell
py -m scripts.init_storage
```

### 7) Створити/оновити admin
```powershell
py -m scripts.seed_admin
```

### 8) Запустити застосунок
```powershell
py -m app.main
```

---

## `config.yaml`: детально по кожному полю

Приклад:

```yaml
app_version: "0.1.0"

database:
  host: "127.0.0.1"
  port: 5432
  dbname: "pwo"
  user: "pwo_user"
  password: "Strong@Pass:2026#local"

storage_root: "D:/PWO/storage"
templates_root: "D:/PWO/templates"
backups_root: "D:/PWO/backups"

pg_dump_path: "C:/Program Files/PostgreSQL/16/bin/pg_dump.exe"
```

### Пояснення
- `database.host` — **тільки host/IP**, наприклад `127.0.0.1` або `192.168.1.50`.
  - ❗ Не можна вказувати `user@host` (наприклад `rk0205@127.0.0.1`) — це зламає підключення.
- `database.port` — порт PostgreSQL, зазвичай `5432`.
- `database.dbname` — назва БД.
- `database.user` / `database.password` — облікові дані PostgreSQL.
- `storage_root` — корінь для файлів подій.
- `templates_root` — шаблони документів.
- `backups_root` — куди складати бекапи.
- `pg_dump_path` — повний шлях до `pg_dump.exe` або просто `pg_dump`, якщо він у `PATH`.

### Приклад для LAN PostgreSQL + UNC
```yaml
database:
  host: "192.168.1.10"
  port: 5432
  dbname: "pwo"
  user: "pwo_user"
  password: "Strong#Pass@2026"

storage_root: "\\\\FS01\\pwo\\storage"
templates_root: "\\\\FS01\\pwo\\templates"
backups_root: "\\\\FS01\\pwo\\backups"

pg_dump_path: "\\\\DB01\\PostgreSQL\\bin\\pg_dump.exe"
```

---

## Порядок резолву конфіга (`config.yaml`)

Застосунок та скрипти шукають конфіг у такому порядку:
1. `PWO_CONFIG` (якщо задано).
2. Для EXE (frozen): `config.yaml` поруч із `PWO.exe`.
3. Для dev-режиму: `config.yaml` у корені проєкту (де є `config.yaml.example`).
4. Fallback: `./config.yaml` у поточній директорії.

Додатково:
- Якщо `PWO_DB_PASSWORD` задано в env, він **перекриває** пароль із `config.yaml`.

---

## PostgreSQL у LAN: обов’язкові налаштування

### 1) `postgresql.conf`
```conf
listen_addresses = '*'
port = 5432
```

### 2) `pg_hba.conf`
Додайте доступ для вашої підмережі:
```conf
host    all    all    192.168.1.0/24    scram-sha-256
```

### 3) Windows Firewall
Створіть inbound rule для TCP 5432 на DB-сервері.

### 4) Перезапуск служби PostgreSQL
Через `services.msc` або:
```powershell
Restart-Service postgresql-x64-16
```

---

## Troubleshooting (реальні польові проблеми)

### 1) `FileNotFoundError: ... config.yaml`
**Симптом:** застосунок/скрипт падає, не знаходить `config.yaml`.

**Причина:**
- файл відсутній;
- файл названо як `config.yaml.txt`;
- запуск із неочікуваної директорії;
- `PWO_CONFIG` вказує на неіснуючий шлях.

**Діагностика:**
```powershell
Get-ChildItem .\config* 
$env:PWO_CONFIG
```

**Фікс:**
```powershell
Copy-Item .\config.yaml.example .\config.yaml
# перевірте, що розширення саме .yaml
```

---

### 2) `ModuleNotFoundError: No module named 'app'` (для `seed_admin.py`)
**Симптом:** помилка імпорту при запуску скрипта.

**Причина:** запуск напряму `python scripts/seed_admin.py` з директорії, де PYTHONPATH не включає корінь проєкту.

**Діагностика:**
```powershell
Get-Location
```

**Фікс (правильний запуск):**
```powershell
py -m scripts.seed_admin
py -m scripts.init_storage
py -m alembic upgrade head
```

---

### 3) `failed to resolve host 'rk0205@127.0.0.1'`
**Симптом:** PostgreSQL-клієнт не може зарезолвити host.

**Причина:** у `database.host` помилково записано `user@host` замість чистого host.

**Діагностика:**
```powershell
Get-Content .\config.yaml
```

**Фікс:**
- `database.host: "127.0.0.1"`
- `database.user: "rk0205"`

---

### 4) `password authentication failed`
**Симптом:** логін до БД не проходить.

**Причина:** неправильний пароль/користувач у `config.yaml` або перевизначення через `PWO_DB_PASSWORD`.

**Діагностика:**
```powershell
$env:PWO_DB_PASSWORD
py -c "from app.services.settings_service import SettingsService; s=SettingsService(SettingsService.resolve_path()); print(s.sqlalchemy_dsn(with_password=False))"
```

**Фікс:**
- звірити `database.user/password` з PostgreSQL;
- прибрати/оновити `PWO_DB_PASSWORD`, якщо він застарілий.

---

### 5) `relation "roles" does not exist`
**Симптом:** seed/admin або app звертається до таблиці, якої нема.

**Причина:** міграції не застосовані до фактичної БД.

**Діагностика:**
```powershell
py -m alembic current
py -m alembic heads
```

**Фікс:**
```powershell
py -m alembic upgrade head
```

---

### 6) `DuplicateObject: type "role_code" already exists` під час `alembic upgrade head`
**Симптом:** падіння initial migration на enum типі.

**Причина:** enum був створений раніше (частково застосована міграція/ручні зміни), а міграція намагалася створити його повторно.

**Фікс у проєкті:** initial migration створює enum-и з `checkfirst=True`, що робить bootstrap більш толерантним до типових dev-сценаріїв.

**Діагностика/повторний запуск:**
```powershell
py -m alembic upgrade head
```

---

### 7) Помилки через вставку Python-коду напряму в PowerShell
**Симптом:** parser error у PS на Python-синтаксисі.

**Причина:** Python вираз вставлено без `py -c` або heredoc.

**Фікс (PowerShell-safe):**
```powershell
py -c "print('ok')"
```
або
```powershell
@'
print("ok")
'@ | py -
```

---

## Build & Deploy EXE

### Збірка
```powershell
.\build\build.ps1
```
або
```bat
build\build.bat
```

### Що має бути у `dist\PWO`
- `PWO.exe`
- Qt/PySide runtime файли (папки/ dll)
- `config.yaml.example`
- `config.yaml` (створюється скриптом, якщо відсутній)

### Розгортання на клієнтських ПК
1. Скопіювати всю папку `dist\PWO`.
2. Відредагувати `config.yaml` під оточення клієнта.
3. Перевірити доступ до БД і UNC шляхів.
4. Запустити `PWO.exe`.

---

## Smoke-test checklist після розгортання

1. `py -m alembic current` показує актуальну ревізію.
2. `py -m scripts.seed_admin` завершується `Admin user ready`.
3. Логін у застосунку працює.
4. Створення тестової події проходить без помилок.
5. Генерація документа з шаблону працює.
6. Backup створює архів у `backups_root`.

---

## FAQ

**Q: Чи можна запускати без PostgreSQL (SQLite)?**
A: Ні, у MVP підтримується лише PostgreSQL.

**Q: Що робити, якщо пароль БД містить `@`, `:`, `/`, `#`, `%`?**
A: Це підтримується; DSN формується безпечно через SQLAlchemy `URL.create(...)`.

**Q: Чому скрипти краще запускати через `py -m ...`?**
A: Щоб коректно резолвились імпорти модуля `app` з кореня проєкту.

---

## Що змінено (changelog)

- Виправлено формування DSN: замість ручної конкатенації використовується безпечний `SQLAlchemy URL.create(...)`.
- Уніфіковано підключення `scripts/seed_admin.py` із загальним механізмом конфіг/DSN.
- У `0001_initial` додано `checkfirst=True` для створення/видалення enum-типів, щоб уникати падінь на `role_code already exists` у типових dev/bootstrap сценаріях.
- README повністю переписано в production-like формат з детальним troubleshooting і PowerShell-safe командами.
