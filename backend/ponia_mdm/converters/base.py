import sqlite3


class Converter:
    """Reads a source directory and loads it into the canonical SQLite model."""

    key = ""
    label = ""

    def import_from(self, src: str, con: sqlite3.Connection) -> int:
        raise NotImplementedError
