# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
import argparse

from . import ops
from .inplace import MdmError
from .review import format_item


def main():
    ap = argparse.ArgumentParser(prog="ponia_mdm", description="Write or remove metadata.ponia.txt next to existing metadata.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("convert", help="write metadata.ponia.txt (originals are not touched)")
    c.add_argument("source", choices=list(ops.SOURCES))
    c.add_argument("path")
    c.add_argument("--trad", action="store_true", help="Simplified -> Traditional Chinese")
    c.add_argument("--engine", choices=["MAME", "FBNeo"], default="MAME",
                   help="where arcade romsets that cannot be identified go (folder source)")

    d = sub.add_parser("delete", help="delete the metadata.ponia.txt files this tool wrote")
    d.add_argument("path")

    a = ap.parse_args()
    if a.cmd == "convert":
        r = ops.convert(a.source, a.path, a.trad, a.engine)
        for n in r["notes"]:
            print(format_item(n))
        print(r["stats"])
    else:
        print("removed:", ops.delete("", a.path))


try:
    main()
except MdmError as e:
    raise SystemExit(f"{e.code}: {e.arg}")
