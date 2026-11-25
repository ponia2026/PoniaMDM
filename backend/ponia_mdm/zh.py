# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Simplified -> Traditional (Taiwan) conversion, literal and conservative.

Engine: OpenCC `s2tw` (pure-python port, dictionaries bundled). It is
phrase-aware, so ambiguous characters resolve by context
(皇后 stays, 以后->以後, 放松->放鬆, 干杯->乾杯, 干部->幹部) and it does NOT
apply Taiwan wording swaps (that would be `s2twp`).

`zh_overrides.json` pins game-title terms the engine gets wrong
(e.g. 魂斗罗 must be 魂斗羅, not 魂鬥羅). Overrides win over the engine.
"""
import json
from functools import lru_cache
import os
import re

_HERE = os.path.dirname(__file__)
_cc = None
_over = None


def _load():
    global _cc, _over
    if _cc is None:
        from opencc import OpenCC
        _cc = OpenCC("s2tw")
        path = os.path.join(_HERE, "zh_overrides.json")
        with open(path, encoding="utf-8") as f:
            _over = json.load(f)
        _over["_rx"] = re.compile(
            "|".join(re.escape(k) for k in sorted(_over["terms"], key=len, reverse=True))
        ) if _over["terms"] else None
    return _cc, _over


_HAS_CJK = re.compile(r"[一-鿿]")


@lru_cache(maxsize=100000)
def to_trad(text):
    if not text or not _HAS_CJK.search(text):
        return text
    cc, over = _load()
    rx = over["_rx"]
    if rx is None:
        return cc.convert(text)
    out, pos = [], 0
    for m in rx.finditer(text):
        out.append(cc.convert(text[pos:m.start()]))
        out.append(over["terms"][m.group(0)])
        pos = m.end()
    out.append(cc.convert(text[pos:]))
    return "".join(out)


# fields that carry human text; everything else (file, paths, ids) is never touched
TEXT_KEYS = {"collection", "game", "description", "developer", "publisher", "genre"}


def convert_pairs(pairs):
    return [(k, to_trad(v) if k in TEXT_KEYS else v) for k, v in pairs]
