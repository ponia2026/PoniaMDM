# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
import argparse
import os

from . import db, inplace
from .review import format_item
from .converters import CONVERTERS
from .exporter import export
from .writer import write_library, undo_moves


def main():
    ap = argparse.ArgumentParser(prog="ponia_mdm")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="Pegasus -> Ponia in place, with backup")
    c.add_argument("root")
    c.add_argument("backup")
    c.add_argument("--keep-pegasus", action="store_true")

    r = sub.add_parser("restore", help="put the backed-up Pegasus metadata back")
    r.add_argument("root")
    r.add_argument("backup")

    i = sub.add_parser("import", help="EmuELEC / user folder -> new Ponia library")
    i.add_argument("source", choices=["emuelec", "folder"])
    i.add_argument("src")
    i.add_argument("out")
    i.add_argument("--roms", choices=["none", "copy", "link", "move"], default="none",
                   help="what to do with ROM files (default: write metadata and media only)")
    i.add_argument("--zh", choices=["keep", "trad"], default="keep",
                   help="trad = Simplified -> Traditional (Taiwan, literal)")
    i.add_argument("--arcade-engine", choices=["MAME", "FBNeo"], default="MAME")

    u = sub.add_parser("undo-move", help="move ROMs back after `import --roms move`")
    u.add_argument("out")

    e = sub.add_parser("export", help="Pegasus -> SQLite -> folder copy")
    e.add_argument("source", choices=["pegasus"])
    e.add_argument("src")
    e.add_argument("out")
    e.add_argument("--no-media", action="store_true")
    e.add_argument("--filename", default="metadata.ponia.txt")

    a = ap.parse_args()
    if a.cmd == "convert":
        print(inplace.convert(a.root, a.backup, a.keep_pegasus))
    elif a.cmd == "restore":
        print("restored folders:", inplace.restore(a.root, a.backup))
    elif a.cmd == "undo-move":
        print("moved back:", undo_moves(a.out))
    elif a.cmd == "import":
        entries, review = CONVERTERS[a.source]().build(a.src, arcade_engine=a.arcade_engine)
        rep = write_library(entries, a.out, a.roms, a.zh == "trad")
        os.makedirs(a.out, exist_ok=True)
        lines = [format_item(x) for x in review + rep["warnings"]]
        with open(os.path.join(a.out, "review.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        for folder, n in rep["folders"].items():
            print(f"{n:5d}  {folder}")
        print(f"{len(entries)} entries, {len(lines)} lines to review -> {a.out}/review.txt")
    else:
        con = db.connect()
        print("imported", CONVERTERS[a.source]().import_from(a.src, con), "games")
        print("collections/games/media: %s/%s/%s" % export(
            con, a.out, a.filename, not a.no_media))


try:
    main()
except inplace.MdmError as e:
    raise SystemExit(f"{e.code}: {e.arg}")
