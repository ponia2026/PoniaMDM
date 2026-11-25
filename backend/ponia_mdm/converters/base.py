import sqlite3


class Converter:
    """A source reader.

    build(src, ...) -> (entries, review): the games found, plus lines for a human to check.
    import_from(src, con) loads the SQLite model (only the Pegasus converter uses it so far).
    """

    key = ""
    label = ""

    def import_from(self, src: str, con: sqlite3.Connection) -> int:
        raise NotImplementedError

    def build(self, src: str, **opts):
        raise NotImplementedError
