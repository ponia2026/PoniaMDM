# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""In-place conversion with a restorable backup.

convert(): backup every metadata.pegasus.txt (byte-exact copy + manifest),
           write metadata.ponia.txt next to it, then remove the Pegasus file.
restore(): copy the backup back and remove the generated metadata.ponia.txt.

Media and ROMs are never touched or copied.
"""
import hashlib
import json
import os
import shutil

from . import metafile, ponia_rules, review, zh


class MdmError(Exception):
    """A user-facing failure: `code` is a translation key, `arg` fills its placeholder."""

    def __init__(self, code, arg=""):
        super().__init__(f"{code}: {arg}")
        self.code, self.arg = code, arg

SRC_NAME = "metadata.pegasus.txt"
DST_NAME = "metadata.ponia.txt"
MANIFEST = "manifest.json"


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _find(root):
    """Relative dir paths ('' = root itself) that hold a Pegasus metadata file."""
    hits = []
    for cur, _dirs, files in os.walk(root):
        if SRC_NAME in files:
            r = os.path.relpath(cur, root).replace("\\", "/")
            hits.append("" if r == "." else r)
    return sorted(hits)


def convert(root, backup_dir, keep_pegasus=False, log=None, trad=False):
    log = log or (lambda it: print(review.format_item(it)))
    root, backup_dir = os.path.abspath(root), os.path.abspath(backup_dir)
    rels = _find(root)
    if not rels:
        raise MdmError("err.no_pegasus", root)
    if os.path.exists(os.path.join(backup_dir, MANIFEST)):
        raise MdmError("err.backup_exists", backup_dir)
    # 1) backup + verify before changing anything
    manifest = {"root": root, "files": {}}
    for rel in rels:
        s = os.path.join(root, rel, SRC_NAME)
        d = os.path.join(backup_dir, rel, SRC_NAME)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        if _sha(s) != _sha(d):
            raise MdmError("err.backup_verify", rel)
        manifest["files"][rel or "."] = _sha(s)
    with open(os.path.join(backup_dir, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    # 2) convert in place
    stats = {"folders": 0, "games": 0, "warnings": 0, "skipped": 0}
    for rel in rels:
        folder = os.path.join(root, rel)
        target = os.path.join(folder, DST_NAME)
        if os.path.exists(target):
            log({"kind": "skip", "rel": rel})
            stats["skipped"] += 1
            continue
        with open(os.path.join(folder, SRC_NAME), encoding="utf-8-sig", newline="") as f:
            sections = metafile.parse(f.read())

        def warn(kind, key, value, rel=rel):
            stats["warnings"] += 1
            log({"kind": kind, "rel": rel, "key": key, "value": value})

        conv = ponia_rules.convert_sections(sections, warn)
        if trad:                                  # Simplified -> Traditional (text fields only)
            conv = [(k, zh.convert_pairs(p)) for k, p in conv]
        with open(target, "w", encoding="utf-8", newline="") as f:
            f.write(metafile.dump(conv, header=ponia_rules.HEADER))
        stats["folders"] += 1
        stats["games"] += sum(1 for k, _ in conv if k == "game")
        if not keep_pegasus:
            os.remove(os.path.join(folder, SRC_NAME))
    return stats


def restore(root, backup_dir, log=print):
    root, backup_dir = os.path.abspath(root), os.path.abspath(backup_dir)
    with open(os.path.join(backup_dir, MANIFEST), encoding="utf-8") as f:
        manifest = json.load(f)
    n = 0
    for rel, digest in manifest["files"].items():
        rel = "" if rel == "." else rel
        s = os.path.join(backup_dir, rel, SRC_NAME)
        if _sha(s) != digest:
            raise MdmError("err.backup_damaged", rel or ".")
        folder = os.path.join(root, rel)
        os.makedirs(folder, exist_ok=True)
        shutil.copy2(s, os.path.join(folder, SRC_NAME))
        gen = os.path.join(folder, DST_NAME)
        if os.path.exists(gen):
            os.remove(gen)
        n += 1
    return n


# ---------------------------------------------------------------- alongside mode (default)
def convert_alongside(root, trad=False, disable_original=False, log=None):
    """Write metadata.ponia.txt next to each metadata.pegasus.txt; the original is not touched.

    disable_original=True renames the Pegasus file to metadata.pegasus.txt.bak afterwards, so a
    frontend that reads both names does not load every game twice.
    """
    log = log or (lambda it: print(review.format_item(it)))
    root = os.path.abspath(root)
    rels = _find(root)
    if not rels:
        raise MdmError("err.no_pegasus", root)
    stats = {"folders": 0, "games": 0, "warnings": 0, "skipped": 0}
    for rel in rels:
        folder = os.path.join(root, rel)
        src = os.path.join(folder, SRC_NAME)
        target = os.path.join(folder, DST_NAME)
        if os.path.exists(target):
            log({"kind": "skip", "rel": rel})
            stats["skipped"] += 1
            if disable_original:
                os.replace(src, src + ".bak")
            continue
        with open(src, encoding="utf-8-sig", newline="") as f:
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
        if disable_original:
            os.replace(src, src + ".bak")
    return stats


def remove_generated(root):
    """Undo convert_alongside: delete the metadata.ponia.txt files this tool wrote (they start with
    our header line) and give any .bak Pegasus file its name back. Returns folders touched."""
    root = os.path.abspath(root)
    n = 0
    for cur, _dirs, files in os.walk(root):
        touched = False
        if DST_NAME in files:
            p = os.path.join(cur, DST_NAME)
            with open(p, encoding="utf-8-sig") as f:
                first = f.readline().strip()
            if first == ponia_rules.HEADER:
                os.remove(p)
                touched = True
        bak = os.path.join(cur, SRC_NAME + ".bak")
        if SRC_NAME + ".bak" in files and SRC_NAME not in files:
            os.replace(bak, os.path.join(cur, SRC_NAME))
            touched = True
        n += touched
    return n
