# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""User settings as one small JSON file.

Portable first: lives in the program's own data folder (_internal next to the exe, which keeps
the exe folder tidy) when that folder is writable, otherwise in %APPDATA%\\PoniaMDM.
Delete the file to reset everything.
"""
import json
import os
import sys

NAME = "PoniaMDM.settings.json"
# theme / lang / tab follow the user automatically. `slots` holds, per source
# (pegasus / emuelec / folder), the latest data folder and options; it is also what
# File > Save file / Open file exchange.
DEFAULTS = {"theme": "system", "lang": "", "tab": "pegasus", "slots": {}}      # lang "" = follow the OS


def _dir():
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None) or os.path.join(os.path.dirname(sys.executable), "_internal")
    else:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    try:
        probe = os.path.join(base, ".w")
        with open(probe, "w"):
            pass
        os.remove(probe)
        return base
    except OSError:
        d = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "PoniaMDM")
        os.makedirs(d, exist_ok=True)
        return d


def folder():
    """Folder holding the settings file; also the default folder for File > Save file."""
    return _dir()


def path():
    return os.path.join(_dir(), NAME)


def load():
    try:
        with open(path(), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    return {**DEFAULTS, **{k: v for k, v in data.items() if k in DEFAULTS}}


def save(data):
    merged = {**load(), **{k: v for k, v in data.items() if k in DEFAULTS}}
    try:
        with open(path(), "w", encoding="utf-8") as f:
            json.dump(merged, f, ensure_ascii=False, indent=1)
    except OSError:
        pass
    return merged
