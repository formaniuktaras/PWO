@echo off
setlocal

if not exist .venv (
  python -m venv .venv
)

call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller pwo.spec --clean

if not exist dist\PWO\config.yaml.example (
  copy /Y config.yaml.example dist\PWO\config.yaml.example >nul
)

if not exist dist\PWO\config.yaml (
  copy /Y dist\PWO\config.yaml.example dist\PWO\config.yaml >nul
)

echo Build complete: dist\PWO
endlocal
