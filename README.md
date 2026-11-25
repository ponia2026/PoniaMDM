# PoniaMDM (Ponia Metadata Manager)

Windows desktop app that converts game metadata into Ponia metadata (`metadata.ponia.txt`).

Stack: Python (FastAPI + pywebview) / Vue 3 (Vite) / SQLite.

## Sources
- Pegasus Frontend (`metadata.pegasus.txt`, `collections.txt`)
- EmuELEC / EmulationStation (`gamelist.xml`)
- A user-supplied folder of ROMs (scan + filename heuristics)

## Layout
- `backend/ponia_mdm/` - API, SQLite schema, converters
- `frontend/` - Vue 3 UI
- `docs/` - Ponia metadata definition

## Windows portable exe
Single file, no install, Windows 10/11 (uses the built-in WebView2 runtime; falls back to the default browser).
Build locally: `powershell -ExecutionPolicy Bypass -File packaging\build_exe.ps1` -> `dist\PoniaMDM.exe`.
CI: pushing a `v*` tag runs .github/workflows/build-windows.yml and attaches PoniaMDM.exe to the release.
