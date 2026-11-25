import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from ponia_mdm import detect, zh


def test_zh_context_not_overtranslated():
    cases = {
        "皇后": "皇后", "以后": "以後", "放松": "放鬆", "干杯": "乾杯", "干部": "幹部",
        "松鼠": "松鼠", "魂斗罗": "魂斗羅", "街头霸王2": "街頭霸王2", "超级马里奥": "超級馬里奧",
    }
    for s, t in cases.items():
        assert zh.to_trad(s) == t, (s, zh.to_trad(s))


def test_zh_keeps_non_text_and_ascii():
    assert zh.to_trad("Super Mario 64") == "Super Mario 64"
    assert zh.convert_pairs([("file", "超级马里奥.nes")]) == [("file", "超级马里奥.nes")]


def _zip(path, names):
    with zipfile.ZipFile(path, "w") as z:
        for n in names:
            z.writestr(n, b"x")


def test_detect_variants(tmp_path):
    (tmp_path / "杂").mkdir()
    (tmp_path / "杂" / "a.nes").write_bytes(b"x")
    (tmp_path / "杂" / "b-hack.smc").write_bytes(b"x")
    _zip(tmp_path / "杂" / "c.zip", ["game.gba"])
    _zip(tmp_path / "杂" / "d.zip", ["d.u1", "d.u2", "d.6"])        # arcade chips
    _zip(tmp_path / "杂" / "e.zip", ["x.bin"])                      # undecided
    (tmp_path / "SFC").mkdir()
    (tmp_path / "SFC" / "f.bin").write_bytes(b"x")                  # ambiguous, folder hint
    iso = bytearray(0x9000)
    iso[0x8001:0x8006] = b"CD001"
    iso[0x8008:0x8008 + 11] = b"PLAYSTATION"
    (tmp_path / "杂" / "g.iso").write_bytes(bytes(iso))
    items, _ = detect.scan(str(tmp_path))
    got = {i.name: (i.platform, i.hack, i.conf) for i in items}
    assert got["a.nes"] == ("FC", False, "high")
    assert got["b-hack.smc"] == ("SFC", True, "high")
    assert got["c.zip"][0] == "GBA"
    assert got["d.zip"] == ("MAME", False, "medium")
    assert got["e.zip"][0] is None
    assert got["f.bin"] == ("SFC", False, "medium")
    assert got["g.iso"] == ("PS1", False, "medium")


def test_cue_owns_its_bin(tmp_path):
    (tmp_path / "PS1").mkdir()
    (tmp_path / "PS1" / "t.bin").write_bytes(b"x")
    (tmp_path / "PS1" / "t.cue").write_text('FILE "t.bin" BINARY\n', encoding="utf-8")
    items, _ = detect.scan(str(tmp_path))
    assert [i.name for i in items] == ["t.cue"]
    assert items[0].companions == ["t.bin"]
