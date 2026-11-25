# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Desktop launcher: local API server + native window (WebView2 via pywebview).

Native menu bar and window icon like an ordinary Windows program. Falls back to
the default browser when no native window is available. Binds to 127.0.0.1 only,
on a free port, unless --lan is given.
"""
import json
import os
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from . import settings
from .main import app

REPO = "https://github.com/ponia2026/PoniaMDM"
HOMEPAGE = REPO
HELP_URL = REPO + "#readme"
COPYRIGHT_URL = REPO + "/blob/main/NOTICE.md"

LANGUAGES = [("en", "English"), ("zh-CN", "简体中文"), ("zh-TW", "繁體中文"), ("es", "Español"),
             ("pt", "Português"), ("ru", "Русский"), ("ja", "日本語"), ("fr", "Français"),
             ("de", "Deutsch")]
# Native menu text; languages without an entry fall back to zh-TW.
MENU_TEXT = {"zh-TW": {
    "file": "檔案(F)", "save_file": "保存檔案", "open_file": "讀取檔案", "exit": "離開(X)",
    "language": "語言(L)", "theme": "主題(T)", "system": "跟隨系統", "light": "淺色", "dark": "深色",
    "help": "說明(H)", "howto": "幫助", "home": "首頁", "copyright": "版權", "about": "關於",
}}
FILE_TYPES = ("PoniaMDM settings (*.json)",)


class Api:
    """Exposed to the page as window.pywebview.api (native dialogs)."""

    def pick_folder(self):
        import webview
        res = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return res[0] if res else None


def _first(res):
    if not res:
        return None
    return res if isinstance(res, str) else res[0]


def save_file(window):
    """File > Save file: write the per-source slots (latest folder and options each) to a file."""
    import webview
    p = _first(window.create_file_dialog(webview.SAVE_DIALOG, directory=settings.folder(), save_filename="PoniaMDM.slots.json",
                                         file_types=FILE_TYPES))
    if not p:
        return
    s = settings.load()
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"app": "PoniaMDM", "version": 1, "tab": s["tab"], "slots": s["slots"]},
                  f, ensure_ascii=False, indent=1)


def open_file(window):
    """File > Open file: replace the slots with the ones stored in a file."""
    import webview
    p = _first(window.create_file_dialog(webview.OPEN_DIALOG, directory=settings.folder(), file_types=FILE_TYPES))
    if not p:
        return
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("app") != "PoniaMDM" or not isinstance(data.get("slots"), dict):
            raise ValueError
    except (OSError, ValueError):
        window.evaluate_js("window.notify('file.invalid')")
        return
    settings.save({"slots": data["slots"], "tab": data.get("tab", "pegasus")})
    window.evaluate_js("window.reloadSlots()")


def _resource(name):
    base = getattr(sys, "_MEIPASS", None) or os.path.join(os.path.dirname(__file__), "..", "..", "packaging")
    return os.path.abspath(os.path.join(base, name))


def _free_port(preferred=8765):
    for p in (preferred, 0):
        s = socket.socket()
        try:
            s.bind(("127.0.0.1", p))
            return s.getsockname()[1]
        except OSError:
            continue
        finally:
            s.close()


def _menu(window):
    from webview.menu import Menu, MenuAction, MenuSeparator

    def js(code):
        return lambda: window.evaluate_js(code)

    def link(url):
        return lambda: webbrowser.open(url)

    m = MENU_TEXT.get(settings.load().get("lang"), MENU_TEXT["zh-TW"])
    return [
        Menu(m["file"], [
            MenuAction(m["save_file"], lambda: save_file(window)),
            MenuAction(m["open_file"], lambda: open_file(window)),
            MenuSeparator(),
            MenuAction(m["exit"], window.destroy),
        ]),
        Menu(m["language"], [MenuAction(name, js(f"window.setLang('{code}')")) for code, name in LANGUAGES]),
        Menu(m["theme"], [
            MenuAction(m["system"], js("window.setTheme('system')")),
            MenuAction(m["light"], js("window.setTheme('light')")),
            MenuAction(m["dark"], js("window.setTheme('dark')")),
        ]),
        Menu(m["help"], [
            MenuAction(m["howto"], link(HELP_URL)),
            MenuAction(m["home"], link(HOMEPAGE)),
            MenuAction(m["copyright"], link(COPYRIGHT_URL)),
            MenuSeparator(),
            MenuAction(m["about"], js("window.openAbout()")),
        ]),
    ]


def run(host="127.0.0.1", headless=False):
    for name in ("stdout", "stderr"):            # --windowed exe has no console streams
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))
    if sys.platform == "win32" and not headless:     # crisp text and correct sizes on scaled displays
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            pass
    port = 8765 if headless else _free_port()
    if headless:
        uvicorn.run(app, host=host, port=port)
        return
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_config=None))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    while not server.started:
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}/"
    try:
        import webview
        win = settings.load()["window"]
        w = webview.create_window("PoniaMDM", url, width=int(win.get("width", 1100)),
                                  height=int(win.get("height", 700)), min_size=(900, 600),
                                  js_api=Api())

        def on_closing():
            try:
                settings.save({"window": {"width": w.width, "height": w.height}})
            except Exception:
                pass

        w.events.closing += on_closing
        ico = _resource("ponia.ico")
        webview.start(menu=_menu(w), icon=ico if os.path.isfile(ico) else None)
    except Exception:
        webbrowser.open(url)
        try:
            t.join()
        except KeyboardInterrupt:
            pass
    server.should_exit = True


if __name__ == "__main__":
    run(host="0.0.0.0" if "--lan" in sys.argv else "127.0.0.1", headless="--headless" in sys.argv)
