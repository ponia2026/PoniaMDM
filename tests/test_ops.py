import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from ponia_mdm import ops

PEG = "collection: FC\r\nextensions: nes\r\n\r\ngame: A\r\nfile: a.nes\r\nrelease: 19850913\r\n"


def test_pegasus_cycle(tmp_path):
    d = tmp_path / "Roms" / "FC"
    d.mkdir(parents=True)
    (d / "metadata.pegasus.txt").write_bytes(PEG.encode("utf-8"))      # bytes: no newline translation on Windows
    root = str(tmp_path / "Roms")
    assert ops.status("pegasus", root)["state"] == "idle"
    assert ops.status("pegasus", str(tmp_path / "gone"))["state"] == "offline"
    assert ops.status("pegasus", "")["state"] == "unset"
    r = ops.convert("pegasus", root)
    assert r["stats"]["games"] == 1
    assert ops.status("pegasus", root)["state"] == "done"
    assert "release: 1985-09-13" in (d / "metadata.ponia.txt").read_text(encoding="utf-8")
    ops.convert("pegasus", root)                       # re-convert overwrites our own file
    assert (d / "metadata.pegasus.txt").read_bytes() == PEG.encode("utf-8")
    (d / "metadata.ponia.txt").write_text("hand written\n", encoding="utf-8")
    assert ops.convert("pegasus", root)["stats"]["skipped"] == 1   # not ours: left alone
    assert ops.delete("pegasus", root) == 0
    assert (d / "metadata.ponia.txt").read_text(encoding="utf-8") == "hand written\n"


def test_folder_cycle_with_override(tmp_path):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "a.nes").write_bytes(b"x")
    (tmp_path / "x" / "b.zip").write_bytes(b"not a zip")
    root = str(tmp_path)
    r = ops.convert("folder", root)
    assert r["stats"]["games"] == 1                    # b.zip is undecided, so not written
    item = next(i for i in r["items"] if i["file"] == "b.zip")
    r = ops.convert("folder", root, overrides={item["src"]: {"platform": "SFC"}})
    assert r["stats"]["games"] == 2
    assert not [n for n in r["notes"] if n.get("path", "").endswith("b.zip")]   # corrected files are no longer flagged
    assert ops.status("folder", root)["state"] == "done"
    assert ops.delete("folder", root) == 1
    assert ops.status("folder", root)["state"] == "idle"


def test_emuelec_bios_entries_are_left_out(tmp_path):
    d = tmp_path / "mame"
    d.mkdir()
    for n in ("neogeo.zip", "pgm.zip", "kof98.zip"):
        (d / n).write_bytes(b"x")
    gl = ("<gameList>"
          "<game><path>./neogeo.zip</path><name>[BIOS] Neo-Geo</name></game>"
          "<game><path>./pgm.zip</path><name>PGM</name></game>"
          "<game><path>./kof98.zip</path><name>KOF 98</name></game>"
          "</gameList>")
    (d / "gamelist.xml").write_bytes(gl.encode("utf-8"))
    ops.convert("emuelec", str(tmp_path))
    out = (d / "metadata.ponia.txt").read_text(encoding="utf-8")
    assert "kof98.zip" in out and "neogeo.zip" not in out and "pgm.zip" not in out
