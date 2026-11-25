"""Ponia platform table (from Ponia.Roms/README.ponia-format.md) and detection hints."""
import re

# key -> collection, folder, sort-by, zip_ok (can the usual core read a .zip of this?)
# Merged collections (ATARI) set `merged` and need `x-system` per game.
PLATFORMS = {
    "MAME":       dict(collection="Arcade - MAME",   sort="010", exts="zip, 7z", zip_ok=True),
    "FBNeo":      dict(collection="Arcade - FBNeo",  sort="012", exts="zip, 7z", zip_ok=True),
    "GB":         dict(collection="GB",   sort="016", exts="gb, zip", zip_ok=True),
    "GBC":        dict(collection="GBC",  sort="017", exts="gbc, zip", zip_ok=True),
    "GBA":        dict(collection="GBA",  sort="018", exts="gba, zip", zip_ok=True),
    "NDS":        dict(collection="NDS",  sort="019", exts="nds, zip", zip_ok=True),
    "FC":         dict(collection="FC",   sort="022", exts="nes, fds, zip, 7z", zip_ok=True),
    "SFC":        dict(collection="SFC",  sort="026", exts="sfc, smc, zip, 7z", zip_ok=True),
    "N64":        dict(collection="N64",  sort="030", exts="z64, n64, v64, zip", zip_ok=True),
    "NGC":        dict(collection="NGC",  sort="031", exts="iso, gcm, ciso, rvz, gcz", zip_ok=False),
    "GG":         dict(collection="GG",   sort="035", exts="gg, zip", zip_ok=True),
    "SMS":        dict(collection="SMS",  sort="036", exts="sms, zip", zip_ok=True),
    "MD":         dict(collection="MD",   sort="037", exts="md, gen, smd, bin, zip", zip_ok=True),
    "SS":         dict(collection="SS",   sort="041", exts="cue, chd, iso", zip_ok=False),
    "DC":         dict(collection="DC",   sort="042", exts="cdi, gdi, chd, cue", zip_ok=False),
    "PSP":        dict(collection="PSP",  sort="043", exts="iso, cso, pbp", zip_ok=False),
    "PS1":        dict(collection="PS1",  sort="045", exts="cue, chd, pbp, iso, m3u", zip_ok=False),
    "PCE":        dict(collection="PCE",  sort="054", exts="pce, sgx, cue, chd, zip", zip_ok=True),
    "WS":         dict(collection="WS",   sort="060", exts="ws, wsc, zip", zip_ok=True),
    "NGPC":       dict(collection="NGPC", sort="058", exts="ngp, ngc, zip", zip_ok=True),
    "LYNX":       dict(collection="LYNX", sort="062", exts="lnx, zip", zip_ok=True),
    "VB":         dict(collection="VB",   sort="029", exts="vb, zip", zip_ok=True),
    "ATARI2600":  dict(collection="ATARI", sort="063", exts="a26, bin, zip, 7z", zip_ok=True, merged="atari2600"),
    "ATARI5200":  dict(collection="ATARI", sort="063", exts="a52, bin, zip, 7z", zip_ok=True, merged="atari5200"),
    "ATARI7800":  dict(collection="ATARI", sort="063", exts="a78, bin, zip, 7z", zip_ok=True, merged="atari7800"),
    "DOS":        dict(collection="DOS",  sort="069", exts="zip, exe, bat, com", zip_ok=True),
    "AppleII":    dict(collection="AppleII", sort="071", exts="dsk, do, po, woz, zip", zip_ok=True),
    "Pico8":      dict(collection="Pico8", sort="072", exts="p8, png", zip_ok=False),
    "Ports":      dict(collection="Ports", sort="080", exts="sh", zip_ok=False),
}
UNSORTED = "Unsorted"       # folder/collection for files we cannot classify

# extensions that identify one platform on their own
UNIQUE_EXT = {
    "nes": "FC", "fds": "FC", "unf": "FC", "unif": "FC",
    "sfc": "SFC", "smc": "SFC", "swc": "SFC", "fig": "SFC",
    "gb": "GB", "gbc": "GBC", "gba": "GBA", "nds": "NDS",
    "z64": "N64", "n64": "N64", "v64": "N64",
    "md": "MD", "gen": "MD", "smd": "MD", "sms": "SMS", "gg": "GG",
    "pce": "PCE", "sgx": "PCE",
    "a26": "ATARI2600", "a52": "ATARI5200", "a78": "ATARI7800",
    "ws": "WS", "wsc": "WS", "ngp": "NGPC", "vb": "VB", "lnx": "LYNX",
    "p8": "Pico8", "gcm": "NGC", "ciso": "NGC", "gcz": "NGC", "rvz": "NGC",
    "cdi": "DC", "gdi": "DC", "cso": "PSP", "pbp": "PSP",
    "dsk": "AppleII", "woz": "AppleII",
}
# disc / generic containers: need a folder hint or a header sniff
AMBIGUOUS_EXT = {"bin", "iso", "cue", "chd", "img", "mdf", "m3u", "zip", "7z", "rom", "ccd"}
ARCHIVE_EXT = {"zip", "7z"}
COMPANION_EXT = {"sub", "ccd", "mds", "srm", "sav", "state", "cfg", "hi", "nv", "nvram"}

# folder-name aliases (normalised: lowercase, only letters/digits/CJK, no 'hack')
_ALIASES = {
    "FC": "fc famicom nes nesh fds 红白机 紅白機 任天堂",
    "SFC": "sfc snes snesh snesmsu1 superfamicom 超任 超级任天堂",
    "GB": "gb gbh gameboy", "GBC": "gbc gbch gameboycolor", "GBA": "gba gbah gameboyadvance",
    "NDS": "nds ds", "N64": "n64 nintendo64", "NGC": "ngc gc gamecube",
    "MD": "md megadrive genesis genh megadrivejapan megadrivemsu 世嘉",
    "SMS": "sms mastersystem", "GG": "gg gamegear gamegearh",
    "SS": "ss saturn segasaturn", "DC": "dc dreamcast", "PSP": "psp pspminis",
    "PS1": "ps1 psx psone playstation", "PCE": "pce pcengine tg16 supergrafx pcenginecd tg16cd",
    "MAME": "mame arcade 街机 街機 mame2003 mame2010", "FBNeo": "fbneo fba fbalpha cps1 cps2 cps3 neogeo capcom pgm2",
    "ATARI2600": "atari2600 a2600", "ATARI5200": "atari5200", "ATARI7800": "atari7800",
    "WS": "ws wsc wonderswan wonderswancolor", "NGPC": "ngp ngpc", "LYNX": "lynx atarilynx",
    "VB": "vb virtualboy", "DOS": "dos pc msdos", "AppleII": "appleii apple2 apple",
    "Pico8": "pico8", "Ports": "ports",
}
ALIAS = {a: k for k, v in _ALIASES.items() for a in v.split()}

_NORM = re.compile(r"[^0-9a-z一-鿿]+")
HACK_RE = re.compile(r"(?i)(?:^|[\s_\-\(\[])hacks?(?:$|[\s_\-\)\]])|改版|修改版")


def norm_folder(name):
    n = HACK_RE.sub(" ", name).lower()
    return _NORM.sub("", n)


def platform_from_folder(name):
    """Platform key for a folder name such as 'FC', 'SFC hack', 'megadrive', else None."""
    return ALIAS.get(norm_folder(name))


def is_hack(name):
    return bool(HACK_RE.search(name))


def folder_name(key, hack):
    return f"{key} hack" if hack else key


def collection_pairs(key, hack):
    p = PLATFORMS.get(key)
    if p is None:                                   # unknown / unsorted
        return [("collection", key), ("sort-by", "099")]
    pairs = [("collection", p["collection"] + (" hack" if hack and not p.get("merged") else ""))]
    if not p.get("merged"):
        pairs.append(("shortname", folder_name(key, False)))
    pairs.append(("sort-by", p["sort"]))
    pairs.append(("extensions", p["exts"]))
    return pairs
