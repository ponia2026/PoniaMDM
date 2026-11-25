# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Write a Ponia library (platform folders + metadata.ponia.txt + media) from entries."""
import json
import os
import shutil
from dataclasses import dataclass, field

from . import metafile, platforms as P, ponia_rules, zh

MEDIA_KINDS = ("boxFront", "logo", "screenshot", "video")


@dataclass
class Entry:
    platform: str
    hack: bool
    title: str
    file: str                       # file name inside the platform folder
    src: str | None = None          # where the ROM is now
    extra_src: list = field(default_factory=list)   # companion files (same dir as src)
    pairs: list = field(default_factory=list)       # extra metadata pairs (developer, ...)
    media: dict = field(default_factory=dict)       # kind -> source path
    bios: bool = False              # goes to ignore-files, not a game
    archive: bool = False
    conf: str = "high"              # how sure the detection is: high / medium / low / none
    reason: str = ""                # evidence for the platform
    notes: list = field(default_factory=list)
    base_dir: str | None = None     # folder that will hold metadata.ponia.txt in in-place mode


ORDER = ["developer", "publisher", "genre", "players", "release", "rating", "description"]


def _transfer(src, dst, mode, journal):
    if mode == "none" or not src or not os.path.exists(src):
        return
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        return
    if mode == "copy":
        shutil.copy2(src, dst)
    elif mode == "move":
        shutil.move(src, dst)
        journal.append([src, dst])
    elif mode == "link":
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)


def write_library(entries, out, roms="none", trad=True, log=print):
    out = os.path.abspath(out)
    journal, report = [], {"warnings": [], "folders": {}}
    groups = {}
    for e in entries:
        groups.setdefault((e.platform, e.hack), []).append(e)

    for (plat, hack), es in sorted(groups.items(), key=lambda kv: (kv[0][0] or "~", kv[0][1])):
        folder = P.folder_name(plat, hack)
        merged = P.PLATFORMS.get(plat, {}).get("merged")
        sections = [("collection", P.collection_pairs(plat, hack))]
        seen, ignore = set(), []
        fdir = os.path.join(out, folder)
        for e in sorted(es, key=lambda x: x.title.lower()):
            if e.file in seen:
                report["warnings"].append({"kind": "DUPLICATE", "folder": folder, "file": e.file})
                continue
            seen.add(e.file)
            _transfer(e.src, os.path.join(fdir, e.file), roms, journal)
            for c in e.extra_src:
                _transfer(c, os.path.join(fdir, os.path.basename(c)), roms, journal)
                ignore.append(os.path.basename(c))
            if e.bios:
                ignore.append(e.file)
                continue
            pairs = [("game", e.title), ("file", e.file)]
            have = dict(e.pairs)
            pairs += [(k, have[k]) for k in ORDER if have.get(k)]
            if merged:
                pairs.append(("x-system", merged))
            sections.append(("game", pairs))
            stem = e.file.rsplit(".", 1)[0] if not e.file.lower().endswith(".p8") else e.file
            for kind, s in e.media.items():
                if s and os.path.isfile(s):
                    ext = os.path.splitext(s)[1].lower()
                    shutil.copy2(s, _ensure(os.path.join(fdir, "media", stem, kind + ext)))
        if ignore:
            sections[0][1].append(("ignore-files", "\n" + "\n".join(sorted(set(ignore)))))
        if trad:
            sections = [(k, zh.convert_pairs(p)) for k, p in sections]
        os.makedirs(fdir, exist_ok=True)
        with open(os.path.join(fdir, "metadata.ponia.txt"), "w", encoding="utf-8", newline="") as f:
            f.write(metafile.dump(sections, header=ponia_rules.HEADER))
        report["folders"][folder] = sum(1 for k, _ in sections if k == "game")
    if journal:
        with open(os.path.join(out, "move_journal.json"), "w", encoding="utf-8") as f:
            json.dump(journal, f, ensure_ascii=False, indent=0)
    return report


def _ensure(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def undo_moves(out):
    """Move files listed in move_journal.json back to where they came from."""
    p = os.path.join(out, "move_journal.json")
    with open(p, encoding="utf-8") as f:
        journal = json.load(f)
    n = 0
    for src, dst in reversed(journal):
        if os.path.exists(dst):
            os.makedirs(os.path.dirname(src), exist_ok=True)
            shutil.move(dst, src)
            n += 1
    return n


def write_inplace(entries, trad=False):
    """Write metadata.ponia.txt next to the ROMs, without moving or copying anything.

    One file per folder. Each platform in that folder gets its own collection that lists its files
    explicitly (`files:`), every game carries `x-system`, and images are referenced where they are
    (`assets.*` paths relative to the metadata file). Files we did not write are never overwritten.
    """
    by_dir, skipped_unsorted = {}, 0
    for e in entries:
        if e.bios or not e.base_dir:
            continue
        if e.platform == P.UNSORTED:
            skipped_unsorted += 1
            continue
        by_dir.setdefault(e.base_dir, []).append(e)
    report = {"warnings": [], "folders": {}}
    for d, es in sorted(by_dir.items()):
        target = os.path.join(d, "metadata.ponia.txt")
        if os.path.exists(target):
            with open(target, encoding="utf-8-sig") as f:
                if f.readline().strip() != ponia_rules.HEADER:
                    report["warnings"].append({"kind": "EXISTING", "path": target})
                    continue
        groups = {}
        for e in es:
            groups.setdefault((e.platform, e.hack), []).append(e)
        sections, n = [], 0
        for (plat, hack), ges in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            head = [(k, v) for k, v in P.collection_pairs(plat, hack) if k not in ("extensions", "shortname")]
            head.append(("files", "\n" + "\n".join(sorted({g.file for g in ges}))))
            sections.append(("collection", head))
            seen = set()
            for e in sorted(ges, key=lambda x: x.title.lower()):
                if e.file in seen:
                    report["warnings"].append({"kind": "DUPLICATE", "folder": d, "file": e.file})
                    continue
                seen.add(e.file)
                pairs = [("game", e.title), ("file", e.file)]
                have = dict(e.pairs)
                pairs += [(k, have[k]) for k in ORDER if have.get(k)]
                if plat in P.PLATFORMS:
                    pairs.append(("x-system", P.PLATFORMS[plat].get("merged") or plat.lower()))
                for kind, key in (("boxFront", "box_front"), ("screenshot", "screenshot"),
                                  ("logo", "logo"), ("video", "video")):
                    s = e.media.get(kind)
                    if s and os.path.isfile(s):
                        pairs.append((f"assets.{key}", os.path.relpath(s, d).replace(os.sep, "/")))
                sections.append(("game", pairs))
                n += 1
        if trad:
            sections = [(k, zh.convert_pairs(p)) for k, p in sections]
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(metafile.dump(sections, header=ponia_rules.HEADER))
        report["folders"][d] = n
    if skipped_unsorted:
        report["warnings"].append({"kind": "UNSORTED_SKIPPED", "n": skipped_unsorted})
    return report
