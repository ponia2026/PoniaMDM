# Build a single-file portable PoniaMDM.exe (Windows). Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
# Needs: Python 3.12 (python.org), Node.js 20+ (skipped when frontend\dist already exists).
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root
if (-not (Test-Path "frontend\dist\index.html")) {
    Push-Location frontend; npm ci; npm run build; Pop-Location
}
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onefile --windowed --name PoniaMDM `
    --paths backend `
    --icon packaging\ponia.ico --add-data "packaging\ponia.ico;." `
    --add-data "NOTICE.md;legal" --add-data "LICENSE.md;legal" `
    --add-data "frontend\dist;frontend_dist" `
    --add-data "backend\ponia_mdm\zh_overrides.json;ponia_mdm" `
    --collect-data opencc `
    --collect-submodules webview `
    --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto `
    --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.lifespan.on `
    backend\run_app.py
Write-Host "Done: dist\PoniaMDM.exe"
