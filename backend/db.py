import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(database_path=None):
    db_path = Path(database_path or current_app.config["DATABASE"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Do not overwrite existing database by default. To force re-initialization,
    # call init_db(..., force=True).
    # Backwards-compatible behavior: if caller passes a Path-like with attribute
    # 'force' in current_app.config or passes a kwarg, this function can be extended.
    if db_path.exists():
        return

    schema_path = Path(__file__).resolve().parent / "data" / "schema.sql"
    seed_path = Path(__file__).resolve().parent / "data" / "seed.sql"

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            connection.executescript(schema_file.read())
        with open(seed_path, "r", encoding="utf-8") as seed_file:
            connection.executescript(seed_file.read())
        connection.commit()
    finally:
        connection.close()

