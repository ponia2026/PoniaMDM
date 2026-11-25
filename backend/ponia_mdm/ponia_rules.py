# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Pegasus -> Ponia field rules (see Ponia.Roms/README.ponia-format.md).

Only mechanical, lossless-in-meaning rewrites live here. Anything we cannot
interpret is kept as-is and reported as a warning.
"""
import re

HEADER = "# Ponia metadata (Pegasus-compatible superset), one file per platform folder"

_DATE8 = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_DATE = re.compile(r"^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$")
_PCT = re.compile(r"^\d{1,3}%$")
_FLOAT = re.compile(r"^(?:0?\.\d+|1(?:\.0+)?|0)$")
_INT = re.compile(r"^\d{1,3}$")

DROP_KEYS = {"launch"}          # Ponia picks the player from the platform, not from launch:
EMPTY_VALUES = {"n/a", "na", "none", "unknown"}


def norm_date(v):
    v = v.strip()
    m = _DATE8.match(v)
    if m:
        return "-".join(m.groups())
    m = _DATE.match(v)
    if m:
        y, mo, d = m.groups()
        return y + (f"-{int(mo):02d}" if mo else "") + (f"-{int(d):02d}" if d else "")
    return None


def norm_rating(v):
    v = v.strip()
    if _PCT.match(v):
        return v
    if _FLOAT.match(v):
        return f"{round(float(v) * 100)}%"
    if _INT.match(v) and int(v) <= 100:
        return f"{int(v)}%"
    return None


def convert_pairs(pairs, warn):
    out = []
    for k, v in pairs:
        if k in DROP_KEYS:
            continue
        if v.strip().lower() in EMPTY_VALUES:
            continue
        if k in ("release", "releasedate"):
            n = norm_date(v)
            if n is None:
                warn("unparsed", k, v)
                if k == "releasedate":
                    continue
                out.append((k, v))
                continue
            k, v = "release", n
        elif k == "rating":
            n = norm_rating(v)
            if n is None:
                warn("unparsed", "rating", v)
            else:
                v = n
        out.append((k, v))
    # releasedate may collide with an existing release; keep the first one
    seen, res = set(), []
    for k, v in out:
        if k == "release":
            if "release" in seen:
                continue
            seen.add("release")
        res.append((k, v))
    return res


def convert_sections(sections, warn=lambda *a: None):
    return [(kind, convert_pairs(pairs, warn)) for kind, pairs in sections]
