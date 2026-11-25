# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Write metadata.ponia.txt next to existing metadata, never touching the originals.

Every file this tool writes starts with a fixed header line, which is how it recognises
its own output later (to overwrite it on re-conversion, or to delete it).
"""
import os

from . import metafile, ponia_rules, review, zh

SRC_NAME = "metadata.pegasus.txt"
DST_NAME = "metadata.ponia.txt"


class MdmError(Exception):
    """A user-facing failure: `code` is a translation key, `arg` fills its placeholder."""

    def __init__(self, code, arg=""):
        super().__init__(f"{code}: {arg}")
        self.code, self.arg = code, arg


def is_ours(path):
    """True when the file at `path` was written by this tool."""
    try:
        with open(path, encoding="utf-8-sig") as f:
            return f.readline().strip() == ponia_rules.HEADER
    except OSError:
        return False


def find_pegasus_dirs(root):
    """Folders under root (and root itself) that hold a metadata.pegasus.txt."""
    hits = []
    for cur, _dirs, files in os.walk(root):
        if SRC_NAME in files:
            hits.append(cur)
    return sorted(hits)


def has_generated(root):
    """True when at least one metadata.ponia.txt written by this tool exists under root."""
    for cur, _dirs, files in os.walk(root):
        if DST_NAME in files and is_ours(os.path.join(cur, DST_NAME)):
            return True
    return False


def convert_pegasus(root, trad=False, log=None):
    """Write metadata.ponia.txt beside each metadata.pegasus.txt.

    Files written by an earlier run are overwritten; a metadata.ponia.txt that this tool did
    not write is left alone and reported.
    """
    log = log or (lambda it: print(review.format_item(it)))
    root = os.path.abspath(root)
    dirs = find_pegasus_dirs(root)
    if not dirs:
        raise MdmError("err.no_pegasus", root)
    stats = {"folders": 0, "games": 0, "warnings": 0, "skipped": 0}
    for folder in dirs:
        rel = os.path.relpath(folder, root)
        rel = "" if rel == "." else rel.replace(os.sep, "/")
        target = os.path.join(folder, DST_NAME)
        if os.path.exists(target) and not is_ours(target):
            log({"kind": "EXISTING", "path": target})
            stats["skipped"] += 1
            continue
        with open(os.path.join(folder, SRC_NAME), encoding="utf-8-sig", newline="") as f:
            sections = metafile.parse(f.read())

        def warn(kind, key, value, rel=rel):
            stats["warnings"] += 1
            log({"kind": kind, "rel": rel, "key": key, "value": value})

        conv = ponia_rules.convert_sections(sections, warn)
        if trad:
            conv = [(k, zh.convert_pairs(p)) for k, p in conv]
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(metafile.dump(conv, header=ponia_rules.HEADER))
        stats["folders"] += 1
        stats["games"] += sum(1 for k, _ in conv if k == "game")
    return stats


def remove_generated(root):
    """Delete every metadata.ponia.txt this tool wrote under root. Returns how many folders."""
    n = 0
    for cur, _dirs, files in os.walk(os.path.abspath(root)):
        if DST_NAME in files:
            p = os.path.join(cur, DST_NAME)
            if is_ours(p):
                os.remove(p)
                n += 1
    return n
