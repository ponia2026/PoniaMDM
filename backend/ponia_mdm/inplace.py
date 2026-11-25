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

from . import metafile, ponia_rules

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


def convert(root, backup_dir, keep_pegasus=False, log=print):
    root, backup_dir = os.path.abspath(root), os.path.abspath(backup_dir)
    rels = _find(root)
    if not rels:
        raise SystemExit(f"no {SRC_NAME} under {root}")
    if os.path.exists(os.path.join(backup_dir, MANIFEST)):
        raise SystemExit(f"backup already exists: {backup_dir} (choose another folder)")
    # 1) backup + verify before changing anything
    manifest = {"root": root, "files": {}}
    for rel in rels:
        s = os.path.join(root, rel, SRC_NAME)
        d = os.path.join(backup_dir, rel, SRC_NAME)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        if _sha(s) != _sha(d):
            raise SystemExit(f"backup verify failed: {rel}")
        manifest["files"][rel or "."] = _sha(s)
    with open(os.path.join(backup_dir, MANIFEST), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    # 2) convert in place
    stats = {"folders": 0, "games": 0, "warnings": 0, "skipped": 0}
    for rel in rels:
        folder = os.path.join(root, rel)
        target = os.path.join(folder, DST_NAME)
        if os.path.exists(target):
            log(f"skip (already has {DST_NAME}): {rel or '.'}")
            stats["skipped"] += 1
            continue
        with open(os.path.join(folder, SRC_NAME), encoding="utf-8-sig", newline="") as f:
            sections = metafile.parse(f.read())

        def warn(m, rel=rel):
            stats["warnings"] += 1
            log(f"warn [{rel or '.'}] {m}")

        conv = ponia_rules.convert_sections(sections, warn)
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
            raise SystemExit(f"backup is damaged: {rel or '.'}")
        folder = os.path.join(root, rel)
        os.makedirs(folder, exist_ok=True)
        shutil.copy2(s, os.path.join(folder, SRC_NAME))
        gen = os.path.join(folder, DST_NAME)
        if os.path.exists(gen):
            os.remove(gen)
        n += 1
    return n
