$ErrorActionPreference = 'Stop'

if (-not (Test-Path '.venv')) {
    python -m venv .venv
}

& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
pyinstaller pwo.spec --clean

if (-not (Test-Path 'dist/PWO/config.yaml.example')) {
    Copy-Item 'config.yaml.example' 'dist/PWO/config.yaml.example' -Force
}

if (-not (Test-Path 'dist/PWO/config.yaml')) {
    Copy-Item 'dist/PWO/config.yaml.example' 'dist/PWO/config.yaml' -Force
}

Write-Host 'Build complete: dist/PWO'
