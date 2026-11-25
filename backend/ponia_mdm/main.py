"""HTTP API for the Vue UI. One in-memory working session (single user, local app)."""
import os
import sys
from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import platforms as P
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


@app.get("/api/sources")
def sources():
    return [{"key": k, "label": c.label} for k, c in CONVERTERS.items() if k != "pegasus"]


@app.get("/api/platforms")
def plats():
    out = [{"key": k, "collection": v["collection"]} for k, v in P.PLATFORMS.items()]
    return out + [{"key": P.UNSORTED, "collection": "未分類"}]


@app.post("/api/scan")
def scan(req: ScanReq):
    if req.source not in ("folder", "emuelec"):
        raise HTTPException(400, "unknown source")
    if not os.path.isdir(req.path):
        raise HTTPException(400, f"資料夾不存在：{req.path}")
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
        raise HTTPException(400, "沒有可匯出的項目")
    rep = write_library(es, req.out, req.roms, req.zh == "trad")
    return rep


def _dist_dir():
    base = getattr(sys, "_MEIPASS", None)          # PyInstaller one-file: unpacked temp dir
    if base:
        return os.path.join(base, "frontend_dist")
    return os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")


_DIST = _dist_dir()
if os.path.isdir(_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST, "assets")), name="assets")

    @app.get("/")
    def index():
        return FileResponse(os.path.join(_DIST, "index.html"))
