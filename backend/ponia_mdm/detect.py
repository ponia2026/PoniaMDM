"""Find games in a user folder and decide their platform.

Evidence, strongest first (the reason is recorded on every item):
  1. extension that belongs to exactly one platform         (.nes, .smc, .z64 ...)
  2. contents of a .zip/.7z (listing only, nothing is extracted)
  3. header of a disc image (.iso/.bin/.cue/.gdi/.chd are ambiguous by name)
  4. name of an enclosing folder (FC, sfc, megadrive, 红白机 ...)
  5. "looks like an arcade romset" (zip of chips with no known extension)
Nothing found -> platform None: the item goes to the Unsorted bucket and is
listed for review. We never guess silently.
"""
import os
import re
import zipfile
from dataclasses import dataclass, field

from . import platforms as P

CONF_RANK = {"high": 3, "medium": 2, "low": 1, "none": 0}
DISC_EXT = {"cue", "iso", "chd", "gdi", "cdi", "img", "mdf", "ccd"}
IGNORE_EXT = {"txt", "pdf", "xlsx", "xls", "doc", "docx", "jpg", "jpeg", "gif", "mp4", "mp3",
              "db", "ini", "nfo", "url", "xml", "json", "md", "log", "bak", "tmp", "srm",
              "sav", "state", "cfg", "hi", "nv"}

# arcade BIOS / device romsets: present in the folder but not games
ARCADE_BIOS = {
    "neogeo", "pgm", "skns", "konamigx", "taitofx1", "megaplay", "megatech", "decocass",
    "cvs", "playch10", "stvbios", "naomi", "naomigd", "awbios", "hng64", "nmk004", "ym2608",
    "cpzn1", "cpzn2", "tps", "midssio", "aristmk5", "isgsm", "f355dlx", "ar_bios", "qsound",
    "pgm2", "cchip", "bubsys", "coh1000c", "coh1002m", "coh3002c", "kviper", "sys246",
}


@dataclass
class Item:
    path: str
    rel: str
    name: str
    platform: str | None = None
    hack: bool = False
    conf: str = "none"
    reason: str = ""
    notes: list = field(default_factory=list)
    companions: list = field(default_factory=list)   # sibling files that belong to this game
    members: list = field(default_factory=list)      # archive listing
    is_bios: bool = False


def ext_of(name):
    low = name.lower()
    if low.endswith(".p8.png"):
        return "p8"
    return low.rsplit(".", 1)[-1] if "." in low else ""


def stem_of(name):
    return name.rsplit(".", 1)[0] if "." in name else name


# --------------------------------------------------------------- archives
def archive_members(path):
    """List member names of a .zip/.7z without extracting. [] when unreadable."""
    ext = ext_of(path)
    try:
        if ext == "zip":
            with zipfile.ZipFile(path) as z:
                out = []
                for i in z.infolist():
                    n = i.filename
                    if not i.flag_bits & 0x800:          # not UTF-8: repair legacy GBK names
                        try:
                            n = n.encode("cp437").decode("gbk")
                        except (UnicodeError, LookupError):
                            pass
                    if not n.endswith("/"):
                        out.append(n)
                return out
        if ext == "7z":
            import py7zr
            with py7zr.SevenZipFile(path) as z:
                return [n for n in z.getnames() if "." in os.path.basename(n)]
    except Exception:
        return []
    return []


def _inner_platform(members):
    """(platform, reason) from archive members, or (None, hint) when undecided."""
    exts = [ext_of(m) for m in members]
    votes = {}
    for e in exts:
        k = P.UNIQUE_EXT.get(e)
        if k:
            votes[k] = votes.get(k, 0) + 1
    if votes:
        k = max(votes, key=votes.get)
        return k, f"archive contains .{next(e for e in exts if P.UNIQUE_EXT.get(e) == k)}"
    if any(e in DISC_EXT for e in exts):
        return None, "disc"
    if exts and all(e == "bin" for e in exts):
        return None, "bin-only"
    if exts:
        return None, "chips"                    # unknown extensions only: arcade-like
    return None, "empty"


# ------------------------------------------------------------- disc sniff
def sniff_disc(path):
    """Platform from the first sectors of an .iso/.bin image, else None."""
    try:
        with open(path, "rb") as f:
            head = f.read(0x9400)
    except OSError:
        return None
    for off in (0, 16):                         # cooked 2048 / raw 2352 sector layouts
        blk = head[off:off + 0x100]
        if blk.startswith(b"SEGA SEGASATURN"):
            return "SS"
        if blk.startswith(b"SEGA SEGAKATANA"):
            return "DC"
    if head[0x1C:0x20] == b"\xc2\x33\x9f\x3d":
        return "NGC"
    pvd = None
    for base in (0x8000, 0x8000 + 16):
        if head[base + 1:base + 6] == b"CD001":
            pvd = head[base + 8:base + 40]
            break
    if pvd is not None:
        if pvd.startswith(b"PSP GAME"):
            return "PSP"
        if pvd.startswith(b"PLAYSTATION"):
            return "PS1"
    return None


def _companions(path, ext):
    """Files referenced by a .cue/.gdi/.m3u (same directory)."""
    d = os.path.dirname(path)
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            txt = f.read(1 << 20)
    except OSError:
        return []
    names = []
    if ext == "cue":
        names = re.findall(r'FILE\s+"([^"]+)"', txt, flags=re.I) or \
            re.findall(r"FILE\s+(\S+)", txt, flags=re.I)
    elif ext == "gdi":
        for line in txt.splitlines()[1:]:
            m = re.match(r'\s*\d+\s+\d+\s+\d+\s+\d+\s+"?([^"]+?)"?\s+\d+\s*$', line)
            if m:
                names.append(m.group(1))
    elif ext == "m3u":
        names = [l.strip() for l in txt.splitlines() if l.strip() and not l.startswith("#")]
    return [n for n in names if os.path.isfile(os.path.join(d, n))]


# ----------------------------------------------------------- classification
def classify(item, hint, hint_hack, arcade_engine="MAME"):
    ext = ext_of(item.name)
    item.hack = hint_hack or P.is_hack(stem_of(item.name))
    item.notes = []

    def set_(plat, conf, why):
        item.platform, item.conf, item.reason = plat, conf, why

    if ext in P.ARCHIVE_EXT:
        item.members = archive_members(item.path)
        inner, why = _inner_platform(item.members)
        base = stem_of(item.name).lower()
        if inner:
            set_(inner, "high", why)
            if hint and hint != inner and not (hint in ("MAME", "FBNeo") and inner == hint):
                item.notes.append(f"folder says {hint}, archive content says {inner}")
            return
        if hint:
            set_(hint, "medium", f"folder name ({why})")
            return
        if why == "chips" and not item.members == []:
            set_(arcade_engine, "medium", "romset of chips: assumed arcade")
            item.is_bios = base in ARCADE_BIOS
            return
        set_(None, "none", f"archive undecided ({why})")
        return

    plat = P.UNIQUE_EXT.get(ext)
    if plat:
        set_(plat, "high", f"extension .{ext}")
        if hint and hint != plat and P.PLATFORMS.get(hint, {}).get("collection") != \
                P.PLATFORMS[plat]["collection"]:
            item.notes.append(f"folder says {hint}, extension says {plat}")
        return

    if ext in DISC_EXT or ext in ("bin", "rom"):
        probe = item.path
        if ext == "cue" and item.companions:
            probe = os.path.join(os.path.dirname(item.path), item.companions[0])
        sniffed = sniff_disc(probe) if ext != "chd" else None
        if sniffed:
            set_(sniffed, "medium", "disc header")
            return
        if hint:
            set_(hint, "medium", "folder name")
            return
    if hint and ext in P.ARCHIVE_EXT | {"rom", "bin"}:
        set_(hint, "low", "folder name")
        return
    set_(None, "none", f"ambiguous .{ext}, no folder hint")


# ------------------------------------------------------------------- scan
def title_from(name):
    """Readable title from a file name: drop extension, hack markers and (region)/[tag] groups."""
    s = stem_of(name)
    s = re.sub(r"(?i)(?:[\s_\-]*[\(\[]?hacks?[\)\]]?)$", "", s)
    s = P.HACK_RE.sub(" ", s)
    cleaned = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", s).strip(" -_")
    return (cleaned or s).strip()


def scan(root, arcade_engine="MAME"):
    """Walk root, return (items, skipped_files)."""
    root = os.path.abspath(root)
    items, skipped = [], []
    for cur, dirs, files in os.walk(root):
        dirs.sort()
        rel_dir = os.path.relpath(cur, root)
        parts = [] if rel_dir == "." else rel_dir.split(os.sep)
        hint, hint_hack = None, False
        for part in parts:                      # deepest recognised folder wins
            if P.is_hack(part):
                hint_hack = True
            k = P.platform_from_folder(part)
            if k:
                hint = k
        owned = set()
        group = []
        for fn in sorted(files):
            ext = ext_of(fn)
            it = Item(path=os.path.join(cur, fn), rel=os.path.relpath(os.path.join(cur, fn), root),
                      name=fn)
            if ext in ("cue", "gdi", "m3u"):
                it.companions = _companions(it.path, ext)
                owned.update(it.companions)
            group.append((fn, ext, it))
        for fn, ext, it in group:
            if fn in owned:
                continue
            known = ext in P.UNIQUE_EXT or ext in P.AMBIGUOUS_EXT
            if not known:
                if ext not in IGNORE_EXT:
                    skipped.append(it.rel)
                continue
            classify(it, hint, hint_hack, arcade_engine)
            items.append(it)
    return items, skipped
