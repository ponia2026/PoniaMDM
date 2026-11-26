# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""PyInstaller entry point.

The windowed exe has no console, so a startup failure would be invisible. Any uncaught error
is written to PoniaMDM.error.log (in the program's data folder, or the temp folder) and shown in a dialog.
"""
import os
import sys
import tempfile
import traceback


def _report(text):
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None) or os.path.join(os.path.dirname(sys.executable), "_internal")
    else:
        base = os.getcwd()
    path = os.path.join(base, "PoniaMDM.error.log")
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        path = os.path.join(tempfile.gettempdir(), "PoniaMDM.error.log")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            path = "(could not write a log file)"
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, f"PoniaMDM could not start / 無法啟動\n\n{text[-900:]}\n\nLog: {path}", "PoniaMDM", 0x10)
    except Exception:
        pass


def _unblock_downloaded_files():
    """A zip downloaded from the web leaves a Zone.Identifier mark on every extracted file, and the .NET
    runtime used for the window refuses to load marked assemblies. Remove the mark from the program folder."""
    if not getattr(sys, "frozen", False) or sys.platform != "win32":
        return
    top = os.path.dirname(sys.executable)
    inner = getattr(sys, "_MEIPASS", None) or os.path.join(top, "_internal")
    for base in (inner, top):
        for dirpath, _dirs, files in os.walk(base):
            for name in files:
                try:
                    os.remove(os.path.join(dirpath, name) + ":Zone.Identifier")
                except OSError:
                    pass
            if base == top:
                break                                    # the exe folder itself: top level only


if __name__ == "__main__":
    try:
        _unblock_downloaded_files()
        from ponia_mdm.app import run
        run()
    except SystemExit:
        raise
    except BaseException:
        _report(traceback.format_exc())
        raise SystemExit(1)
