import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "branik.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                date    TEXT,
                home    TEXT NOT NULL,
                away    TEXT NOT NULL,
                home_goals INTEGER NOT NULL,
                away_goals INTEGER NOT NULL,
                UNIQUE(date, home, away)
            )
        """)


def upsert_match(date: str, home: str, away: str, home_goals: int, away_goals: int) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO matches (date, home, away, home_goals, away_goals)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date, home, away) DO UPDATE SET
                home_goals = excluded.home_goals,
                away_goals = excluded.away_goals
        """, (date, home, away, home_goals, away_goals))


def all_matches() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM matches ORDER BY id"
        ).fetchall()
