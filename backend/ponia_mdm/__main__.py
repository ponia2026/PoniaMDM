import argparse

from . import db, inplace
from .converters import CONVERTERS
from .exporter import export


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

    e = sub.add_parser("export", help="import a source into SQLite and export a folder copy")
    e.add_argument("source", choices=sorted(CONVERTERS))
    e.add_argument("src")
    e.add_argument("out")
    e.add_argument("--no-media", action="store_true")
    e.add_argument("--filename", default="metadata.ponia.txt")

    a = ap.parse_args()
    if a.cmd == "convert":
        print(inplace.convert(a.root, a.backup, a.keep_pegasus))
    elif a.cmd == "restore":
        print("restored folders:", inplace.restore(a.root, a.backup))
    else:
        con = db.connect()
        print("imported", CONVERTERS[a.source]().import_from(a.src, con), "games")
        print("collections/games/media: %s/%s/%s" % export(
            con, a.out, a.filename, not a.no_media))


main()
