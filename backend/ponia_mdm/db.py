"""SQLite storage: the canonical Ponia metadata model.

Every section of a metadata file keeps its ordered (key, value) pairs in a
JSON column, so unknown keys survive a round trip untouched.
"""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS collection (
    id INTEGER PRIMARY KEY,
    dir TEXT NOT NULL,            -- absolute source directory
    reldir TEXT NOT NULL,         -- directory name relative to the source root
    ord INTEGER NOT NULL,
    name TEXT,
    fields TEXT NOT NULL          -- JSON [[key, value], ...]
);
CREATE TABLE IF NOT EXISTS game (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER NOT NULL REFERENCES collection(id) ON DELETE CASCADE,
    ord INTEGER NOT NULL,
    title TEXT,
    file TEXT,
    fields TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_game_col ON game(collection_id, ord);
"""


def connect(path: str = ":memory:") -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    return con
