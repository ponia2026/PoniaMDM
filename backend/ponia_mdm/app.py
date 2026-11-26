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

HOMEPAGE = "https://ponia.org/product/poniamdm/"
HELP_URL = "https://ponia.org/docs/poniamdm/"
COPYRIGHT_URL = "https://ponia.org/about/poniamdm-notice/"

LANGUAGES = [("en", "English"), ("zh-CN", "简体中文"), ("zh-TW", "繁體中文"), ("es", "Español"),
             ("pt", "Português"), ("ru", "Русский"), ("ja", "日本語"), ("fr", "Français"),
             ("de", "Deutsch")]
# Native menu text, one entry per language; the menu is rebuilt when the language changes.
_K = ("file", "save_file", "open_file", "exit", "language", "theme", "system", "light", "dark",
      "help", "howto", "home", "copyright", "about")
MENU_TEXT = {code: dict(zip(_K, values)) for code, values in {
    "zh-TW": ("檔案(F)", "保存檔案", "讀取檔案", "離開(X)", "語言(L)", "主題(T)", "跟隨系統", "淺色", "深色",
              "說明(H)", "幫助", "首頁", "版權", "關於"),
    "zh-CN": ("文件(F)", "保存文件", "读取文件", "退出(X)", "语言(L)", "主题(T)", "跟随系统", "浅色", "深色",
              "帮助(H)", "使用说明", "首页", "版权", "关于"),
    "en": ("File", "Save file", "Open file", "Exit", "Language", "Theme", "Follow system", "Light", "Dark",
           "Help", "How to use", "Home", "Copyright", "About"),
    "es": ("Archivo", "Guardar archivo", "Abrir archivo", "Salir", "Idioma", "Tema", "Seguir el sistema", "Claro", "Oscuro",
           "Ayuda", "Cómo usarlo", "Página principal", "Derechos de autor", "Acerca de"),
    "pt": ("Arquivo", "Salvar arquivo", "Abrir arquivo", "Sair", "Idioma", "Tema", "Seguir o sistema", "Claro", "Escuro",
           "Ajuda", "Como usar", "Página inicial", "Direitos autorais", "Sobre"),
    "ru": ("Файл", "Сохранить файл", "Открыть файл", "Выход", "Язык", "Тема", "Как в системе", "Светлая", "Тёмная",
           "Справка", "Как пользоваться", "Главная страница", "Авторские права", "О программе"),
    "ja": ("ファイル", "ファイルを保存", "ファイルを開く", "終了", "言語", "テーマ", "システムに合わせる", "ライト", "ダーク",
           "ヘルプ", "使い方", "ホームページ", "著作権", "バージョン情報"),
    "fr": ("Fichier", "Enregistrer le fichier", "Ouvrir un fichier", "Quitter", "Langue", "Thème", "Suivre le système", "Clair", "Sombre",
           "Aide", "Mode d’emploi", "Page d’accueil", "Droits d’auteur", "À propos"),
    "de": ("Datei", "Datei speichern", "Datei öffnen", "Beenden", "Sprache", "Design", "System folgen", "Hell", "Dunkel",
           "Hilfe", "Anleitung", "Startseite", "Urheberrecht", "Über"),
}.items()}


def _os_lang():
    """UI language of the operating system, mapped to one of the supported codes (English otherwise)."""
    name = ""
    if sys.platform == "win32":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(85)
            ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85)
            name = buf.value
        except Exception:
            pass
    low = name.lower()
    if low.startswith("zh"):
        return "zh-TW" if any(x in low for x in ("tw", "hk", "mo", "hant")) else "zh-CN"
    base = low.split("-")[0]
    return base if base in MENU_TEXT else "en"
FILE_TYPES = ("PoniaMDM settings (*.json)",)


class Api:
    """Exposed to the page as window.pywebview.api (native dialogs)."""

    def pick_folder(self):
        import webview
        res = webview.windows[0].create_file_dialog(webview.FOLDER_DIALOG)
        return res[0] if res else None

    def refresh_menu(self, code):
        """Rebuild the menu bar in another language (the menu is otherwise fixed when the window opens)."""
        import webview
        from System import Func, Type
        from System.Windows.Forms import MenuStrip
        window = webview.windows[0]
        form = window.native
        items = _menu(window, code)

        def work():
            for c in list(form.Controls):
                if isinstance(c, MenuStrip):
                    form.Controls.Remove(c)
                    c.Dispose()
            form.set_window_menu(items)
        form.Invoke(Func[Type](work))


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
    p = _pick_open(window) or _first(window.create_file_dialog(
        webview.OPEN_DIALOG, directory=settings.folder(), file_types=FILE_TYPES))
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


DEFAULT_FILE = "PoniaMDM.slots.json"


def _pick_open(window):
    """Windows "Open" dialog with the default file name already filled in (Open is one click away).

    Returns the chosen path, or None when cancelled or when the native call is unavailable
    (the caller then falls back to the generic dialog).
    """
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD), ("hwndOwner", wintypes.HWND), ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR), ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD), ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR), ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR), ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR), ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD), ("nFileOffset", wintypes.WORD), ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR), ("lCustData", wintypes.LPARAM), ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR), ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD), ("FlagsEx", wintypes.DWORD),
        ]

    try:
        folder = settings.folder()
        buf = ctypes.create_unicode_buffer(DEFAULT_FILE, 1024)
        flt = ctypes.create_unicode_buffer("PoniaMDM settings (*.json)\0*.json\0\0", 64)
        try:
            owner = int(window.native.Handle.ToInt64())
        except Exception:
            owner = 0
        ofn = OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(OPENFILENAMEW)
        ofn.hwndOwner = owner
        ofn.lpstrFilter = ctypes.cast(flt, wintypes.LPCWSTR)
        ofn.nFilterIndex = 1
        ofn.lpstrFile = ctypes.cast(buf, wintypes.LPWSTR)
        ofn.nMaxFile = 1024
        ofn.lpstrInitialDir = folder
        ofn.Flags = 0x00001000 | 0x00000800 | 0x00080000 | 0x00000008   # file/path must exist, explorer style, keep cwd
        if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn)):
            return buf.value
    except Exception:
        return None
    return ""


def _window_size():
    """Logical (width, height) that gives a 1200 x 900 pixel window, limited to the usable screen area."""
    want_w, want_h = 1200, 900
    scale = 1.0
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            scale = ctypes.windll.user32.GetDpiForSystem() / 96.0
            rect = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)   # SPI_GETWORKAREA
            want_w = min(want_w, rect.right - rect.left)
            want_h = min(want_h, rect.bottom - rect.top)
        except Exception:
            pass
    return int(want_w / scale), int(want_h / scale)


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


def _menu(window, lang=None):
    from webview.menu import Menu, MenuAction, MenuSeparator

    def js(code):
        return lambda: window.evaluate_js(code)

    def link(url):
        return lambda: webbrowser.open(url)

    m = MENU_TEXT.get(lang or settings.load().get("lang") or _os_lang(), MENU_TEXT["en"])
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
        width, height = _window_size()           # the default size is also the minimum size
        w = webview.create_window("PoniaMDM", url, width=width, height=height,
                                  min_size=(width, height), js_api=Api())
        ico = _resource("ponia.ico")
        webview.start(menu=_menu(w), icon=ico if os.path.isfile(ico) else None)
    except Exception:
        import traceback
        text = traceback.format_exc()
        path = os.path.join(settings.folder(), "PoniaMDM.window.log")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            path = "(could not write a log file)"
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0, "The window could not be created. Please make sure Microsoft Edge WebView2 Runtime is installed."
                + chr(10) * 2 + text[-700:] + chr(10) * 2 + "Log: " + path,
                "PoniaMDM", 0x10)
        except Exception:
            pass
    server.should_exit = True


if __name__ == "__main__":
    run(host="0.0.0.0" if "--lan" in sys.argv else "127.0.0.1", headless="--headless" in sys.argv)
