# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""Desktop launcher: local API server + native window (WebView2 via pywebview).

Native menu bar and window icon like an ordinary Windows program. Falls back to
the default browser when no native window is available. Binds to 127.0.0.1 only,
on a free port, unless --lan is given.
"""
import os
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from . import settings
from .main import app

HOMEPAGE = "https://github.com/ponia2026/PoniaMDM"


class Api:
    """Exposed to the page as window.pywebview.api (native dialogs)."""

    def pick_folder(self):
        import webview
        res = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return res[0] if res else None


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

    return [
        Menu("檔案(F)", [MenuAction("離開(X)", window.destroy)]),
        Menu("主題(T)", [
            MenuAction("跟隨系統", js("window.setTheme('system')")),
            MenuAction("淺色", js("window.setTheme('light')")),
            MenuAction("深色", js("window.setTheme('dark')")),
        ]),
        Menu("說明(H)", [
            MenuAction("專案首頁", lambda: webbrowser.open(HOMEPAGE)),
            MenuSeparator(),
            MenuAction("關於與授權", js("window.openAbout()")),
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
