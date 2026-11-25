# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
"""PyInstaller entry point.

The windowed exe has no console, so a startup failure would be invisible. Any uncaught error
is written to PoniaMDM.error.log (next to the exe, or in the temp folder) and shown in a dialog.
"""
import os
import sys
import tempfile
import traceback


def _report(text):
    base = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.getcwd()
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


if __name__ == "__main__":
    try:
        from ponia_mdm.app import run
        run()
    except SystemExit:
        raise
    except BaseException:
        _report(traceback.format_exc())
        raise SystemExit(1)
