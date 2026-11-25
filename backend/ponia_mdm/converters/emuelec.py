# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""EmuELEC / EmulationStation: <roms>/<system>/gamelist.xml (+ images/, videos/)."""
import os
import re
import xml.etree.ElementTree as ET

from .base import Converter
from .folder import entry_from_item, review_lines
from .. import detect, platforms as P
from ..writer import Entry

SKIP_DIRS = {"bios", "bezels", "downloads", "savestates", "screenshots", "splash", "bgm",
             "system volume information", "$recycle.bin"}
HACK_DIRS = {"ips", "hack", "hacks"}
_DATE = re.compile(r"^(\d{4})(\d{2})(\d{2})")


def _text(g, tag):
    e = g.find(tag)
    return e.text.strip() if e is not None and e.text and e.text.strip() else None


def _rating(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f"{round(f * 100)}%" if 0 < f <= 1 else None


def _release(v):
    m = _DATE.match(v or "")
    if not m or m.group(1) == "1970":           # ES writes 1970-01-01 for "unknown"
        return None
    y, mo, d = m.groups()
    if d != "01" or mo != "01":
        return f"{y}-{mo}-{d}"
    return y


def _players(v):
    return v.replace(" ", "") if v and re.fullmatch(r"\d+([\-–]\d+)?", v.replace(" ", "")) else None


def _media(sysdir, g):
    def p(tag):
        t = _text(g, tag)
        if not t:
            return None
        f = os.path.normpath(os.path.join(sysdir, t))
        return f if os.path.isfile(f) else None
    thumb, image = p("thumbnail"), p("image")
    return {k: v for k, v in {
        "boxFront": thumb or image,
        "screenshot": image if thumb else None,
        "logo": p("marquee"),
        "video": p("video"),
    }.items() if v}


class EmuelecConverter(Converter):
    key = "emuelec"
    label = "EmuELEC (gamelist.xml)"

    def build(self, src, arcade_engine="MAME", **_):
        src = os.path.abspath(src)
        entries, review = [], []
        for sysname in sorted(os.listdir(src)):
            sysdir = os.path.join(src, sysname)
            if not os.path.isdir(sysdir) or sysname.lower() in SKIP_DIRS:
                continue
            plat = P.platform_from_folder(sysname)
            hack_sys = P.is_hack(sysname)
            if plat is None:
                plat = sysname.upper()
            listed, missing = set(), []
            gl =os.path.join(sysdir, "gamelist.xml")
            if os.path.isfile(gl):
                try:
                    root = ET.parse(gl).getroot()
                except ET.ParseError as e:
                    review.append(f"BADXML     {sysname}/gamelist.xml ({e})")
                    root = None
                for g in (root.findall("game") if root is not None else []):
                    path = _text(g, "path")
                    if not path or (_text(g, "hidden") or "").lower() == "true":
                        continue
                    rel = os.path.normpath(path)
                    full = os.path.join(sysdir, rel)
                    listed.add(os.path.normcase(os.path.abspath(full)))
                    if not os.path.isfile(full):
                        missing.append(f"{sysname}/{rel}")
                        continue
                    parts = [x.lower() for x in rel.split(os.sep)[:-1]]
                    hack = hack_sys or bool(HACK_DIRS & set(parts)) or P.is_hack(detect.stem_of(os.path.basename(rel)))
                    ent = Entry(platform=plat, hack=hack,
                                title=_text(g, "name") or detect.title_from(os.path.basename(rel)),
                                file=rel.replace(os.sep, "/"), src=full, media=_media(sysdir, g),
                                archive=detect.ext_of(rel) in P.ARCHIVE_EXT,
                                conf="high", reason="EmuELEC system folder + gamelist.xml")
                    pairs = {
                        "developer": _text(g, "developer"), "publisher": _text(g, "publisher"),
                        "genre": _text(g, "genre"), "players": _players(_text(g, "players")),
                        "release": _release(_text(g, "releasedate")),
                        "rating": _rating(_text(g, "rating")), "description": _text(g, "desc"),
                    }
                    ent.pairs = [(k, v) for k, v in pairs.items() if v]
                    entries.append(ent)
            if missing:
                review.append(f"MISSING    {sysname}: {len(missing)} listed in gamelist but not on disk, "
                              f"e.g. {', '.join(missing[:3])}")
            # files the gamelist does not know: classify them like a user folder
            hint_items = []
            for fn in sorted(os.listdir(sysdir)):
                full = os.path.join(sysdir, fn)
                if not os.path.isfile(full) or os.path.normcase(os.path.abspath(full)) in listed:
                    continue
                ext = detect.ext_of(fn)
                if ext not in P.UNIQUE_EXT and ext not in P.AMBIGUOUS_EXT:
                    continue
                it = detect.Item(path=full, rel=f"{sysname}/{fn}", name=fn)
                if ext in ("cue", "gdi", "m3u"):
                    it.companions = detect._companions(full, ext)
                detect.classify(it, plat if plat in P.PLATFORMS else None, hack_sys, arcade_engine)
                hint_items.append(it)
            owned = {c for it in hint_items for c in it.companions}
            hint_items = [i for i in hint_items if i.name not in owned]
            # keep EmuELEC's own system as the platform for generic containers
            for it in hint_items:
                if it.platform is None and plat in P.PLATFORMS:
                    it.platform, it.conf, it.reason = plat, "low", "system folder"
            entries += [entry_from_item(i) for i in hint_items]
            review += review_lines(hint_items, [])
        return entries, review
