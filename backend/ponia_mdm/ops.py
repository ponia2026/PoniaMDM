# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""The three operations behind the UI: status, convert, delete. One code path per source."""
import os

from . import inplace, platforms as P
from .converters import CONVERTERS
from .inplace import MdmError
from .writer import write_inplace

SOURCES = ("pegasus", "emuelec", "folder")
SOLID = {"folder", "ext", "arch_ext", "sysfolder", "emuelec_list", "manual"}
MAX_ITEMS = 300


def needs_check(e):
    """Entries a person should look at: unknown platform, conflicts, or guessed evidence."""
    if e.bios:
        return False
    return (e.platform == P.UNSORTED or bool(e.notes)
            or (e.conf in ("low", "medium", "none") and e.reason.split("|")[0] not in SOLID))


def status(source, path, quick=False):
    """state: unset (no path) / offline (path not reachable) / idle (nothing written yet) / done.

    quick=True only checks reachability and returns state "online" instead of scanning.
    """
    if source not in SOURCES:
        raise MdmError("err.unknown_source")
    if not path:
        return {"state": "unset"}
    if not os.path.isdir(path):
        return {"state": "offline"}
    if quick:
        return {"state": "online"}
    info = {}
    if source == "pegasus":
        info["folders"] = len(inplace.find_pegasus_dirs(path))
    elif source == "emuelec":
        try:
            info["folders"] = sum(
                1 for d in os.listdir(path)
                if os.path.isfile(os.path.join(path, d, "gamelist.xml")))
        except OSError:
            return {"state": "offline"}
    return {"state": "done" if inplace.has_generated(path) else "idle", **info}


def _apply_overrides(entries, overrides, root):
    """Apply manual corrections; returns the relative paths that were corrected."""
    done = set()
    for e in entries:
        o = overrides.get(e.src or "")
        if o:
            e.platform = o.get("platform") or e.platform
            e.hack = bool(o.get("hack", e.hack))
            e.conf, e.reason, e.notes = "high", "manual", []
            done.add(os.path.relpath(e.src, root))
    return done


def convert(source, path, trad=False, engine="MAME", overrides=None):
    if source not in SOURCES:
        raise MdmError("err.unknown_source")
    if not path or not os.path.isdir(path):
        raise MdmError("err.folder_missing", path)
    if source == "pegasus":
        notes = []
        stats = inplace.convert_pegasus(path, trad, log=notes.append)
        return {"stats": stats, "notes": notes, "items": [], "more": 0}
    entries, review = CONVERTERS[source]().build(path, arcade_engine=engine)
    fixed = _apply_overrides(entries, overrides or {}, os.path.abspath(path))
    review = [x for x in review
              if not (x.get("kind") in ("UNSORTED", "GUESS", "CONFLICT") and x.get("path") in fixed)]
    rep = write_inplace(entries, trad)
    notes = review + rep["warnings"]
    items = [{"src": e.src, "file": e.file, "title": e.title, "platform": e.platform, "hack": e.hack,
              "conf": e.conf, "reason": e.reason, "notes": e.notes}
             for e in entries if needs_check(e)]
    stats = {"folders": len(rep["folders"]), "games": sum(rep["folders"].values()),
             "skipped": sum(1 for w in rep["warnings"] if w["kind"] == "EXISTING"), "warnings": len(notes)}
    return {"stats": stats, "notes": notes, "items": items[:MAX_ITEMS], "more": max(0, len(items) - MAX_ITEMS)}


def delete(source, path):
    if not path or not os.path.isdir(path):
        raise MdmError("err.folder_missing", path)
    return inplace.remove_generated(path)
