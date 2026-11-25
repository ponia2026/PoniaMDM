# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Equuleus Works


class Converter:
    """A source reader: build(src) -> (entries, review), where review lists things to check."""

    key = ""

    def build(self, src, **opts):
        raise NotImplementedError
