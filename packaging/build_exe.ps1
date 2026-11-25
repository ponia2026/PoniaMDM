# Build the portable PoniaMDM folder for Windows. Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1
# Output:
#   dist\PoniaMDM\PoniaMDM.exe   run it from the folder (settings are saved next to the exe)
#   dist\PoniaMDM-portable.zip   the same folder, zipped for download
# Needs: Python 3.12 (python.org), Node.js 20+ (skipped when frontend\dist already exists).
$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\.."
Set-Location $root
if (-not (Test-Path "frontend\dist\index.html")) {
    Push-Location frontend; npm ci; npm run build; Pop-Location
}
python -m pip install -r requirements.txt

# stamp the release date shown in Help > About, and put it back afterwards
$info = "backend\ponia_mdm\buildinfo.py"
$original = Get-Content $info -Raw
$date = Get-Date -Format "yyyy/MM/dd"
$original -replace 'RELEASE = ".*"', "RELEASE = `"$date`"" | Set-Content $info -NoNewline -Encoding utf8
try {
    python -m PyInstaller --noconfirm --clean --windowed --onedir --name PoniaMDM `
        --paths backend `
        --icon packaging\ponia.ico --add-data "packaging\ponia.ico;." `
        --add-data "frontend\dist;frontend_dist" `
        --add-data "backend\ponia_mdm\zh_overrides.json;ponia_mdm" `
        --collect-data opencc `
        --collect-submodules webview `
        --hidden-import uvicorn.logging --hidden-import uvicorn.loops.auto `
        --hidden-import uvicorn.protocols.http.auto --hidden-import uvicorn.lifespan.on `
        backend\run_app.py
} finally {
    Set-Content $info $original -NoNewline -Encoding utf8
}

# the license texts travel with the program
Copy-Item LICENSE.md, NOTICE.md "dist\PoniaMDM" -Force
Compress-Archive -Path "dist\PoniaMDM" -DestinationPath "dist\PoniaMDM-portable.zip" -Force
Write-Host "Done: dist\PoniaMDM\PoniaMDM.exe and dist\PoniaMDM-portable.zip"
