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
