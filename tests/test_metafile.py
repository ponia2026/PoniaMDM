import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from ponia_mdm import metafile

SAMPLE = (
    "collection: FC\r\nextensions: nes, zip\r\nlaunch: am start\r\n  -n a/b\r\n"
    "  -e ROM {file.path}\r\n\r\ngame: A\r\nfile: a.zip\r\ndescription: hello: world\r\n\r\n"
    "game: B\r\nfile: b.zip\r\nignore-files: \r\n  x.zip\r\n"
)


def test_roundtrip():
    s = metafile.parse(SAMPLE)
    assert len(s) == 3
    assert dict(s[0][1])["launch"] == "am start\n-n a/b\n-e ROM {file.path}"
    assert dict(s[1][1])["description"] == "hello: world"
    assert metafile.parse(metafile.dump(s)) == s


def test_two_digit_year():
    from ponia_mdm import ponia_rules as r
    assert r.norm_date("96-5-24") == "1996-05-24"
    assert r.norm_date("04-2-17") == "2004-02-17"
    assert r.norm_date("89-1-1") == "1989-01-01"
    assert r.norm_date("1996-5-24") == "1996-05-24"
    assert r.norm_date("Action") is None
    assert r.norm_date("12-25") is None          # month-day only: not guessed
    assert r.norm_date("96-13-40") is None       # impossible month/day
