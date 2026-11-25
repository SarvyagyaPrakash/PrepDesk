import logging
import os
import sqlite3
from pathlib import Path

logger = logging.getLogger("prepdesk.db")

_BASE_DIR = Path(__file__).resolve().parent
_DEFAULT_DB_PATH = _BASE_DIR / "data" / "prepdesk.db"

_CREATE_APPLICATIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company TEXT NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('wishlist', 'applied', 'oa', 'interview', 'offer', 'rejected')
    ),
    link TEXT,
    notes TEXT,
    created_at TEXT,
    updated_at TEXT
);
"""

_CREATE_DEADLINES_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS deadlines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    course TEXT,
    due_date TEXT NOT NULL,
    created_at TEXT
);
"""


def get_db_path() -> Path:
    """Resolve the SQLite database path from PREPDESK_DB or default to data/prepdesk.db."""
    env_path = os.environ.get("PREPDESK_DB")
    if env_path:
        return Path(env_path)
    return _DEFAULT_DB_PATH


def get_connection() -> sqlite3.Connection:
    """Open a SQLite connection, ensure the data directory and schema exist, and enable dict-like rows."""
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    logger.debug("Opening SQLite database at %s", db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(_CREATE_APPLICATIONS_TABLE_SQL)
    conn.execute(_CREATE_DEADLINES_TABLE_SQL)
    conn.commit()
    return conn
