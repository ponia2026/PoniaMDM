# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""User settings as one small JSON file.

Portable first: lives next to the exe (PoniaMDM.settings.json) when that folder is
writable, otherwise in %APPDATA%\\PoniaMDM. Delete the file to reset everything.
"""
import json
import os
import sys

NAME = "PoniaMDM.settings.json"
# theme / lang / window follow the user automatically; "defaults" is the saved form
# (File > Save as defaults) that the app restores on start and on File > Load defaults.
DEFAULTS = {"theme": "system", "lang": "zh-TW", "defaults": {},
            "window": {"width": 1100, "height": 700}}


def _dir():
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else \
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
