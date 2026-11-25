"""Export the SQLite model as a restorable backup folder.

The layout mirrors the source root, so copying the whole folder back over
the ROM root restores everything:

    <out>/<collection dir>/metadata.ponia.txt
    <out>/<collection dir>/media/...        (copied as-is)
"""
import json
import os
import shutil

from . import metafile

SKIP = {"thumbs.db", "desktop.ini", ".ds_store"}


def _copy_media(src_dir, dst_dir):
    n = 0
    for root, _dirs, files in os.walk(src_dir):
        rel = os.path.relpath(root, src_dir)
        os.makedirs(os.path.join(dst_dir, rel), exist_ok=True)
        for f in files:
            if f.lower() in SKIP:
                continue
            s, d = os.path.join(root, f), os.path.join(dst_dir, rel, f)
            if os.path.exists(d) and os.stat(d).st_size == os.stat(s).st_size:
                continue                        # already backed up
            shutil.copy2(s, d)
            n += 1
    return n


def export(con, out_dir, filename="metadata.ponia.txt", with_media=True):
    """Write one folder per collection. Returns (collections, games, media_files_copied)."""
    cols = games = media = 0
    by_dir = {}                                 # a folder may hold several collection sections
    for c in con.execute("SELECT * FROM collection ORDER BY ord, id"):
        by_dir.setdefault(c["reldir"], []).append(c)
    for reldir, group in by_dir.items():
        sections = []
        for c in group:
            pairs = [tuple(p) for p in json.loads(c["fields"])]
            if pairs:
                sections.append(("collection", pairs))
            for g in con.execute(
                    "SELECT fields FROM game WHERE collection_id=? ORDER BY ord", (c["id"],)):
                sections.append(("game", [tuple(p) for p in json.loads(g["fields"])]))
                games += 1
        dst = os.path.join(out_dir, reldir)
        os.makedirs(dst, exist_ok=True)
        with open(os.path.join(dst, filename), "w", encoding="utf-8", newline="") as f:
            f.write(metafile.dump(sections))
        cols += 1
        m = os.path.join(group[0]["dir"], "media")
        if with_media and os.path.isdir(m):
            media += _copy_media(m, os.path.join(dst, "media"))
    return cols, games, media
