# Build PoniaMDM for Windows. Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
# Output:
#   dist\PoniaMDM.exe           single file (unpacks itself to %TEMP% on every start)
#   dist\PoniaMDM-portable.zip  folder build: unzip anywhere and run; starts faster and is not
#                               affected by antivirus software locking the unpacked files
# Needs: Python 3.12 (python.org), Node.js 20+ (skipped when frontend\dist already exists).
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root
if (-not (Test-Path "frontend\dist\index.html")) {
    Push-Location frontend; npm ci; npm run build; Pop-Location
}
python -m pip install -r requirements.txt

$common = @(
    "--noconfirm", "--clean", "--windowed", "--name", "PoniaMDM",
    "--paths", "backend",
    "--icon", "packaging\ponia.ico", "--add-data", "packaging\ponia.ico;.",
    "--add-data", "NOTICE.md;legal", "--add-data", "LICENSE.md;legal",
    "--add-data", "frontend\dist;frontend_dist",
    "--add-data", "backend\ponia_mdm\zh_overrides.json;ponia_mdm",
    "--collect-data", "opencc",
    "--collect-submodules", "webview",
    "--hidden-import", "uvicorn.logging", "--hidden-import", "uvicorn.loops.auto",
    "--hidden-import", "uvicorn.protocols.http.auto", "--hidden-import", "uvicorn.lifespan.on"
)

python -m PyInstaller @common --onefile backend\run_app.py
Write-Host "Done: dist\PoniaMDM.exe"

python -m PyInstaller @common --onedir --distpath dist\onedir --workpath build\onedir backend\run_app.py
Compress-Archive -Path "dist\onedir\PoniaMDM" -DestinationPath "dist\PoniaMDM-portable.zip" -Force
Write-Host "Done: dist\PoniaMDM-portable.zip"
