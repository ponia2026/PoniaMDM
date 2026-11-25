# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works
from .base import Converter
from .pegasus import PegasusConverter
from .emuelec import EmuelecConverter
from .folder import FolderConverter

CONVERTERS = {c.key: c for c in (PegasusConverter, EmuelecConverter, FolderConverter)}
__all__ = ["Converter", "CONVERTERS"]
