# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""HTTP API for the Vue UI. One in-memory working session (single user, local app)."""
import os
import sys
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import inplace, platforms as P, settings
from .converters import CONVERTERS
from .writer import write_library

app = FastAPI(title="PoniaMDM")
S = {"rows": [], "review": [], "source": None, "src": None}


class ScanReq(BaseModel):
    source: str
    path: str
    arcade_engine: str = "MAME"


class UpdateReq(BaseModel):
    ids: list[int]
    platform: str | None = None
    hack: bool | None = None
    include: bool | None = None
    title: str | None = None


class ExportReq(BaseModel):
    out: str
    roms: str = "none"
    zh: str = "keep"


def _row(i, r):
    e = r["e"]
    return {"id": i, "title": e.title, "file": e.file, "src": e.src, "platform": e.platform,
            "hack": e.hack, "conf": e.conf, "reason": e.reason, "notes": e.notes,
            "archive": e.archive, "bios": e.bios, "include": r["include"],
            "edited": r["edited"], "media": list(e.media)}


class PegasusReq(BaseModel):
    root: str
    backup: str
    keep_pegasus: bool = False
    trad: bool = False


def _legal_dir():
    base = getattr(sys, "_MEIPASS", None)
    return os.path.join(base, "legal") if base else os.path.join(os.path.dirname(__file__), "..", "..")


@app.get("/api/settings")
def get_settings():
    return settings.load()


@app.post("/api/settings")
def post_settings(data: dict):
    return settings.save(data)


@app.get("/api/about")
def about():
    d = _legal_dir()
    txt = {}
    for k, f in (("notice", "NOTICE.md"), ("license", "LICENSE.md")):
        try:
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                txt[k] = fh.read()
        except OSError:
            txt[k] = ""
    from . import __version__
    return {"version": __version__, **txt}


@app.post("/api/pegasus/convert")
def pegasus_convert(req: PegasusReq):
    if not os.path.isdir(req.root):
        raise HTTPException(400, f"err.folder_missing|{req.root}")
    if not req.backup.strip():
        raise HTTPException(400, "err.backup_required")
    log = []
    try:
        stats = inplace.convert(req.root, req.backup, req.keep_pegasus, log=log.append, trad=req.trad)
    except SystemExit as e:
        raise HTTPException(400, "err.raw|" + str(e))
    return {"stats": stats, "log": log}


@app.post("/api/pegasus/restore")
def pegasus_restore(req: PegasusReq):
    try:
        n = inplace.restore(req.root, req.backup)
    except SystemExit as e:
        raise HTTPException(400, "err.raw|" + str(e))
    except OSError as e:
        raise HTTPException(400, f"err.backup_not_found|{e}")
    return {"restored": n}


@app.get("/api/sources")
def sources():
    order = ["pegasus", "folder", "emuelec"]
    return [{"key": k, "label": CONVERTERS[k].label} for k in order]


@app.get("/api/platforms")
def plats():
    out = [{"key": k, "collection": v["collection"]} for k, v in P.PLATFORMS.items()]
    return out + [{"key": P.UNSORTED, "collection": "未分類"}]


@app.post("/api/scan")
def scan(req: ScanReq):
    if req.source not in ("folder", "emuelec"):
        raise HTTPException(400, "err.unknown_source")
    if not os.path.isdir(req.path):
        raise HTTPException(400, f"err.folder_missing|{req.path}")
    entries, review = CONVERTERS[req.source]().build(req.path, arcade_engine=req.arcade_engine)
    S.update(rows=[{"e": e, "include": True, "edited": False,
                    "orig": (e.platform, e.hack)} for e in entries],
             review=review, source=req.source, src=req.path)
    return {"count": len(entries), "review": len(review)}


@app.get("/api/entries")
def entries():
    return {"rows": [_row(i, r) for i, r in enumerate(S["rows"])], "review": S["review"],
            "source": S["source"], "src": S["src"]}


@app.post("/api/entries/update")
def update(req: UpdateReq):
    for i in req.ids:
        if not 0 <= i < len(S["rows"]):
            continue
        r = S["rows"][i]
        e = r["e"]
        if req.platform is not None:
            e.platform = req.platform
            e.conf, e.reason = "high", "manual"
            e.notes = []
        if req.hack is not None:
            e.hack = req.hack
        if req.include is not None:
            r["include"] = req.include
        if req.title is not None:
            e.title = req.title
        if req.platform is not None or req.hack is not None or req.title is not None:
            r["edited"] = True
    return {"ok": True}


@app.post("/api/export")
def export(req: ExportReq):
    es = [r["e"] for r in S["rows"] if r["include"]]
    if not es:
        raise HTTPException(400, "err.nothing_to_export")
    rep = write_library(es, req.out, req.roms, req.zh == "trad")
    return rep


def _dist_dir():
    base = getattr(sys, "_MEIPASS", None)          # PyInstaller one-file: unpacked temp dir
    if base:
        return os.path.join(base, "frontend_dist")
    return os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")


_DIST = _dist_dir()
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="ui")   # after all /api routes
