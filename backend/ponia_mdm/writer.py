# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Write metadata.ponia.txt next to the ROMs, without moving or copying anything."""
import os
from dataclasses import dataclass, field

from . import metafile, platforms as P, ponia_rules, zh
from .inplace import is_ours


@dataclass
class Entry:
    platform: str
    hack: bool
    title: str
    file: str                       # path of the ROM relative to base_dir
    src: str | None = None          # absolute path of the ROM
    extra_src: list = field(default_factory=list)   # companion files (same folder as src)
    pairs: list = field(default_factory=list)       # extra metadata pairs (developer, ...)
    media: dict = field(default_factory=dict)       # kind -> source path
    bios: bool = False              # not a game: never written
    archive: bool = False
    conf: str = "high"              # how sure the detection is: high / medium / low / none
    reason: str = ""                # evidence for the platform (see review.REASONS)
    notes: list = field(default_factory=list)
    base_dir: str | None = None     # folder that holds the metadata file


ORDER = ["developer", "publisher", "genre", "players", "release", "rating", "description"]
MEDIA_KEYS = (("boxFront", "box_front"), ("screenshot", "screenshot"), ("logo", "logo"), ("video", "video"))


def write_inplace(entries, trad=False):
    """One metadata.ponia.txt per folder.

    Each platform in a folder gets its own collection that lists its files explicitly (`files:`),
    every game carries `x-system`, and images are referenced where they are (`assets.*` paths
    relative to the metadata file). Files not written by this tool are never overwritten.
    Returns {"folders": {dir: games}, "warnings": [review items]}.
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
        if os.path.exists(target) and not is_ours(target):
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
                for kind, key in MEDIA_KEYS:
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
