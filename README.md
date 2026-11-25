# PoniaMDM (Ponia Metadata Manager)

Windows desktop app that converts game metadata into Ponia metadata (`metadata.ponia.txt`).

Stack: Python (FastAPI + pywebview) / Vue 3 (Vite).

## Sources
- Pegasus Frontend (`metadata.pegasus.txt`)
- EmuELEC / EmulationStation (`gamelist.xml`)
- A user-supplied folder of ROMs (scan + file name heuristics)

Each source gets a `metadata.ponia.txt` written next to the existing metadata; originals, images and ROMs are never
modified. A re-run overwrites only files this tool wrote, and "Delete data" removes only those.

## Layout
- `backend/ponia_mdm/` - API, detection, converters, writer
- `frontend/` - Vue 3 UI (`src/locales/` holds the UI strings, zh-TW is the source language)
- `docs/` - Ponia metadata definition and the PoniaGDB plan

## Run from source
```
cd frontend && npm install && npm run build
cd ../backend && python3 -m ponia_mdm.app            # native window (pywebview), browser fallback
python3 -m ponia_mdm.app --headless --lan            # server only, open http://<host>:8765/
python3 -m ponia_mdm convert pegasus <roms folder>   # command line: pegasus | emuelec | folder
```

## Windows portable build
Unzip `PoniaMDM-portable.zip` anywhere and run `PoniaMDM.exe`: no installer, settings are saved in the `_internal` folder next to the exe
(Windows 10/11; uses the built-in WebView2 runtime and falls back to the default browser).

Build locally: `powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1` produces `dist\PoniaMDM-portable.zip`.
CI: pushing a `v*` tag runs `.github/workflows/build-windows.yml` and attaches the zip to the release.
