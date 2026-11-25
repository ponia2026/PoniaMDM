# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Import Pegasus metadata: <root>/<collection dir>/metadata.pegasus.txt."""
import json
import os

from .base import Converter
from .. import metafile

NAMES = ("metadata.pegasus.txt", "metadata.ponia.txt")


def find_metadata(dirpath):
    for n in NAMES:
        p = os.path.join(dirpath, n)
        if os.path.isfile(p):
            return p
    return None


def _first(pairs, key):
    return next((v for k, v in pairs if k == key), None)


class PegasusConverter(Converter):
    key = "pegasus"
    label = "Pegasus"

    def import_from(self, src, con):
        """src = a root holding one sub-folder per collection, or a single collection folder."""
        src = os.path.abspath(src)
        dirs = [src] if find_metadata(src) else sorted(
            os.path.join(src, d) for d in os.listdir(src)
            if os.path.isdir(os.path.join(src, d)))
        count = 0
        for ci, d in enumerate(dirs):
            mp = find_metadata(d)
            if not mp:
                continue
            with open(mp, encoding="utf-8-sig", newline="") as f:
                sections = metafile.parse(f.read())
            cid = None
            gi = 0
            for kind, pairs in sections:
                j = json.dumps(pairs, ensure_ascii=False)
                if kind == "collection":
                    cid = con.execute(
                        "INSERT INTO collection(dir,reldir,ord,name,fields) VALUES(?,?,?,?,?)",
                        (d, os.path.basename(d), ci, _first(pairs, "collection"), j)).lastrowid
                    continue
                if cid is None:     # games without a collection header
                    cid = con.execute(
                        "INSERT INTO collection(dir,reldir,ord,name,fields) VALUES(?,?,?,?,?)",
                        (d, os.path.basename(d), ci, os.path.basename(d), "[]")).lastrowid
                con.execute(
                    "INSERT INTO game(collection_id,ord,title,file,fields) VALUES(?,?,?,?,?)",
                    (cid, gi, _first(pairs, "game"), _first(pairs, "file"), j))
                gi += 1
                count += 1
        con.commit()
        return count
