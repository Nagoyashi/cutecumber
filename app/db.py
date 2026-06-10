"""SQLite access layer. Raw sqlite3, no ORM, parameterised queries only.

Rules (see DECISIONS.md):
- One connection per request, opened lazily, closed on teardown.
- WAL mode + busy_timeout: many readers, one writer, single box.
- Every query against a user-scoped table (links, and anything future)
  MUST include `AND user_id = ?`. No exceptions. This is the IDOR line.
"""

import sqlite3

import click
from flask import current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        conn = sqlite3.connect(current_app.config["DATABASE"])
        conn.row_factory = sqlite3.Row
        # journal_mode persists in the DB file, but re-issuing is free and
        # protects against a DB file created outside init-db.
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        g.db = conn
    return g.db


def close_db(_exc: BaseException | None = None) -> None:
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db() -> None:
    """Apply schema.sql, then upgrade existing tables. Idempotent both ways:
    schema uses CREATE ... IF NOT EXISTS, and upgrades only add what's missing,
    so `flask init-db` is always safe to re-run."""
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    # Column upgrades for DBs created before the column existed. Table and DDL
    # are code literals, never user input.
    _ensure_column(db, "users", "avatar_value", "TEXT NOT NULL DEFAULT '🥒'")
    db.commit()


def _ensure_column(db: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    existing = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


@click.command("init-db")
def init_db_command() -> None:
    init_db()
    click.echo("database ready 🥒")


def init_app(app) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
