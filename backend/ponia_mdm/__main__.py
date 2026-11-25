import argparse

from . import db
from .converters import CONVERTERS
from .exporter import export


def main():
    ap = argparse.ArgumentParser(prog="ponia_mdm")
    ap.add_argument("source", choices=sorted(CONVERTERS))
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--db", default=":memory:")
    ap.add_argument("--no-media", action="store_true")
    ap.add_argument("--filename", default="metadata.ponia.txt")
    a = ap.parse_args()
    con = db.connect(a.db)
    n = CONVERTERS[a.source]().import_from(a.src, con)
    print(f"imported {n} games")
    print("exported collections/games/media: %s/%s/%s" % export(
        con, a.out, a.filename, not a.no_media))


main()
