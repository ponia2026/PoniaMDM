"""Reader/writer for Pegasus-style metadata text (also used by metadata.ponia.txt)."""
import re

_KEY = re.compile(r"^([^\s:#][^:]*?)\s*:\s?(.*)$")
SECTION_KEYS = ("collection", "game")


def parse(text: str):
    """Return a list of sections: [(kind, [(key, value), ...]), ...].

    kind is 'collection' or 'game'. Continuation lines are joined with '\\n'.
    """
    sections = []
    cur = None          # pairs of the current section
    for raw in text.lstrip("﻿").splitlines():
        if not raw.strip():
            continue
        if raw[0] in " \t":                     # continuation of the previous value
            if cur:
                k, v = cur[-1]
                cur[-1] = (k, v + "\n" + raw.strip())
            continue
        if raw.startswith("#"):
            continue
        m = _KEY.match(raw)
        if not m:
            continue
        key, val = m.group(1).strip(), m.group(2).rstrip()
        if key in SECTION_KEYS:
            cur = []
            sections.append((key, cur))
        elif cur is None:                       # keys before any section: implicit collection
            cur = []
            sections.append(("collection", cur))
        cur.append((key, val))
    return sections


def dump(sections) -> str:
    """Serialize sections back to text with CRLF line endings."""
    out = []
    for _kind, pairs in sections:
        for k, v in pairs:
            lines = v.split("\n")
            out.append(f"{k}: {lines[0]}" if lines[0] else f"{k}:")
            out.extend("  " + l for l in lines[1:])
        out.append("")
    return "\r\n".join(out) + "\r\n"
