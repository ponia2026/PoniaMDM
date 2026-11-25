"""User-organised ROM folder: detect games and platforms from the files themselves."""
import os

from .base import Converter
from .. import detect, platforms as P
from ..writer import Entry


def entry_from_item(it):
    arch = detect.ext_of(it.name) in P.ARCHIVE_EXT
    return Entry(platform=it.platform or P.UNSORTED, hack=it.hack,
                 title=detect.title_from(it.name), file=it.name, src=it.path,
                 extra_src=[os.path.join(os.path.dirname(it.path), c) for c in it.companions],
                 bios=it.is_bios, archive=arch, conf=it.conf, reason=it.reason,
                 notes=list(it.notes))


def review_lines(items, skipped):
    """Things a human should look at: weak evidence, conflicts, unsupported archives."""
    out = []
    for it in items:
        plat = it.platform
        if plat is None:
            out.append(f"UNSORTED   {it.rel}  ({it.reason})")
            continue
        if it.conf in ("low", "medium") and not it.is_bios and "folder" not in it.reason \
                and "extension" not in it.reason and "archive contains" not in it.reason:
            out.append(f"GUESS      {it.rel}  -> {plat}  ({it.reason})")
        for n in it.notes:
            out.append(f"CONFLICT   {it.rel}  {n}")
        ext = detect.ext_of(it.name)
        if ext == "7z":
            out.append(f"7Z         {it.rel}  (players usually cannot read .7z; repack as .zip)")
        elif ext == "zip" and plat in P.PLATFORMS and not P.PLATFORMS[plat]["zip_ok"]:
            out.append(f"ZIP        {it.rel}  ({plat} cores normally cannot read .zip)")
    out += [f"SKIPPED    {s}  (unknown file type)" for s in skipped]
    return out


class FolderConverter(Converter):
    key = "folder"
    label = "自訂資料夾"

    def build(self, src, arcade_engine="MAME", **_):
        items, skipped = detect.scan(src, arcade_engine)
        entries = [entry_from_item(i) for i in items]
        return entries, review_lines(items, skipped)
