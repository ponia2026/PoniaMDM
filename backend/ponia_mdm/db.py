"""SQLite storage: the canonical Ponia metadata model."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS collection (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    shortname TEXT,
    extensions TEXT,
    launch TEXT
);
CREATE TABLE IF NOT EXISTS game (
    id INTEGER PRIMARY KEY,
    collection_id INTEGER REFERENCES collection(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    file TEXT NOT NULL,
    developer TEXT, publisher TEXT, genre TEXT,
    players TEXT, release TEXT, rating TEXT,
    description TEXT, source TEXT
);
CREATE TABLE IF NOT EXISTS asset (
    game_id INTEGER REFERENCES game(id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    path TEXT NOT NULL
);
"""


def connect(path: str = "ponia_mdm.db") -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    return con
