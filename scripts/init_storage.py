from pathlib import Path

from app.services.settings_service import SettingsService


def main() -> None:
    cfg = SettingsService(Path("config.yaml")).config
    for p in [Path(cfg.storage_root), Path(cfg.templates_root), Path(cfg.backups_root)]:
        p.mkdir(parents=True, exist_ok=True)
    (Path(cfg.storage_root) / "events").mkdir(exist_ok=True)
    print("Storage directories initialized")


if __name__ == "__main__":
    main()
