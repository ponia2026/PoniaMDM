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
