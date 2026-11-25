"""Desktop launcher: local API server + native window (WebView2 via pywebview).

Falls back to the default browser when no native window is available.
Binds to 127.0.0.1 only, on a free port, so nothing is exposed to the network
unless --lan is given.
"""
import os
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from .main import app


class Api:
    """Exposed to the page as window.pywebview.api (native dialogs)."""

    def pick_folder(self):
        import webview
        w = webview.windows[0]
        res = w.create_file_dialog(webview.FOLDER_DIALOG)
        return res[0] if res else None


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


def run(host="127.0.0.1", headless=False):
    for name in ("stdout", "stderr"):            # --windowed exe has no console streams
        if getattr(sys, name) is None:
            setattr(sys, name, open(os.devnull, "w"))
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
        webview.create_window("PoniaMDM", url, width=1280, height=820, js_api=Api())
        webview.start()
    except Exception:
        webbrowser.open(url)
        try:
            t.join()
        except KeyboardInterrupt:
            pass
    server.should_exit = True


if __name__ == "__main__":
    run(host="0.0.0.0" if "--lan" in sys.argv else "127.0.0.1", headless="--headless" in sys.argv)
