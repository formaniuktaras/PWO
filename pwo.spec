# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

project_root = Path.cwd()

qt_datas, qt_binaries, qt_hiddenimports = collect_all("PySide6")
qt_extra_datas = collect_data_files("PySide6")
qt_extra_hiddenimports = collect_submodules("PySide6")

datas = qt_datas + qt_extra_datas + [
    (str(project_root / "config.yaml.example"), "."),
]

readme_path = project_root / "README.md"
if readme_path.exists():
    datas.append((str(readme_path), "."))

a = Analysis(
    ['app/main.py'],
    pathex=[str(project_root)],
    binaries=qt_binaries,
    datas=datas,
    hiddenimports=sorted(set(qt_hiddenimports + qt_extra_hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PWO',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PWO',
)
