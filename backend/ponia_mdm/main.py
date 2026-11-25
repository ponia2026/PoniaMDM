# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""HTTP API for the Vue UI (local, single user)."""
import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import __version__, ops, platforms as P, settings
from .inplace import MdmError

app = FastAPI(title="PoniaMDM")


class PathReq(BaseModel):
    source: str
    path: str = ""
    quick: bool = False


class ConvertReq(PathReq):
    trad: bool = False
    engine: str = "MAME"
    overrides: dict = {}


def _fail(e):
    return HTTPException(400, f"{e.code}|{e.arg}")


@app.get("/api/settings")
def get_settings():
    return settings.load()


@app.post("/api/settings")
def post_settings(data: dict):
    return settings.save(data)


@app.get("/api/platforms")
def platforms():
    out = [{"key": k, "collection": v["collection"]} for k, v in P.PLATFORMS.items()]
    return out + [{"key": P.UNSORTED, "collection": "Unsorted"}]


@app.get("/api/about")
def about():
    try:
        from . import buildinfo
        release = buildinfo.RELEASE
    except ImportError:
        release = ""
    return {"version": __version__, "release": release}


@app.post("/api/status")
def status(req: PathReq):
    try:
        return ops.status(req.source, req.path, req.quick)
    except MdmError as e:
        raise _fail(e)


@app.post("/api/convert")
def convert(req: ConvertReq):
    try:
        return ops.convert(req.source, req.path, req.trad, req.engine, req.overrides)
    except MdmError as e:
        raise _fail(e)


@app.post("/api/delete")
def delete(req: PathReq):
    try:
        return {"removed": ops.delete(req.source, req.path)}
    except MdmError as e:
        raise _fail(e)


def _dist_dir():
    base = getattr(sys, "_MEIPASS", None)          # PyInstaller: unpacked resources
    if base:
        return os.path.join(base, "frontend_dist")
    return os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")


_DIST = _dist_dir()
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="ui")   # after all /api routes
