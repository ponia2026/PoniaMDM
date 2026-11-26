import os
import re

LOCALES = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "locales")
CODES = ["en", "zh-CN", "es", "pt", "ru", "ja", "fr", "de"]
LINE = re.compile(r"^  '([^']+)': '((?:[^'\\]|\\.)*)',$", re.M)


def load(code):
    text = open(os.path.join(LOCALES, code + ".js"), encoding="utf-8").read()
    return {m.group(1): m.group(2) for m in LINE.finditer(text)}


def placeholders(s):
    return sorted(re.findall(r"\{(\w+)\}", s))


def test_every_language_covers_the_source_keys_with_the_same_placeholders():
    src = load("zh-TW")
    assert len(src) > 80
    for code in CODES:
        tr = load(code)
        extra = set(tr) - set(src)
        assert not extra, (code, extra)
        for key, val in tr.items():
            assert placeholders(val) == placeholders(src[key]), (code, key, val)
        missing = set(src) - set(tr) - {"opt.trad"}      # the Traditional-Chinese switch is shown in Chinese UIs only
        assert not missing, (code, sorted(missing))


def test_tab_labels_fit_the_fixed_tab_column():
    src = load("zh-TW")
    for code in CODES + ["zh-TW"]:
        tr = load(code)
        for key in ("tab.pegasus", "tab.emuelec", "tab.folder"):
            val = tr.get(key) or src[key]
            assert len(val) <= 14, (code, key, val)
