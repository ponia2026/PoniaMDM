# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Review / warning items are plain dicts with a `kind` and parameters, so the UI can translate
them. This module renders the same items as English text for the command line and review.txt."""

REASONS = {
    "ext": "extension .{a}",
    "arch_ext": "archive contains .{a}",
    "folder": "folder name",
    "disc_header": "disc image header",
    "arcade_guess": "romset of chips: assumed arcade",
    "arch_undecided": "archive content undecided",
    "ambiguous": "ambiguous .{a}, no folder hint",
    "sysfolder": "system folder",
    "emuelec_list": "EmuELEC system folder + gamelist.xml",
    "manual": "set manually",
    "conflict_ext": "folder says {a}, extension says {b}",
    "conflict_arch": "folder says {a}, archive content says {b}",
}


def reason_en(code):
    key, *args = str(code).split("|")
    tpl = REASONS.get(key)
    if tpl is None:
        return str(code)
    return tpl.format(a=args[0] if args else "", b=args[1] if len(args) > 1 else "")


def format_item(it):
    k = it["kind"]
    if k == "UNSORTED":
        return f"UNSORTED   {it['path']}  ({reason_en(it['reason'])})"
    if k == "GUESS":
        return f"GUESS      {it['path']}  -> {it['plat']}  ({reason_en(it['reason'])})"
    if k == "CONFLICT":
        return f"CONFLICT   {it['path']}  {reason_en(it['note'])}"
    if k == "ARCHIVE7Z":
        return f"7Z         {it['path']}  (players usually cannot read .7z; repack as .zip)"
    if k == "ZIPDISC":
        return f"ZIP        {it['path']}  ({it['plat']} cores normally cannot read .zip)"
    if k == "SKIPPED":
        return f"SKIPPED    {it['path']}  (unknown file type)"
    if k == "MISSING":
        return (f"MISSING    {it['system']}: {it['n']} listed in gamelist but not on disk, "
                f"e.g. {', '.join(it['examples'])}")
    if k == "BADXML":
        return f"BADXML     {it['path']} ({it['error']})"
    if k == "DUPLICATE":
        return f"DUPLICATE  duplicate file name in {it['folder']}: {it['file']}"
    if k == "EXISTING":
        return f"EXISTING   {it['path']} was not written by this tool; left untouched"
    if k == "UNSORTED_SKIPPED":
        return f"UNSORTED   {it['n']} files of unknown platform were not written"
    if k == "unparsed":
        return f"warn [{it['rel'] or '.'}] unparsed {it['key']}: {it['value']!r}"
    if k == "skip":
        return f"skip (already has metadata.ponia.txt): {it['rel'] or '.'}"
    return str(it)
