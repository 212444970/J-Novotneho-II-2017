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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS next_round (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                round   TEXT,
                date    TEXT,
                home    TEXT NOT NULL,
                away    TEXT NOT NULL
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


def save_next_round(round_label: str, matches: list[dict]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM next_round")
        for m in matches:
            conn.execute(
                "INSERT INTO next_round (round, date, home, away) VALUES (?, ?, ?, ?)",
                (round_label, m["date"], m["home"], m["away"])
            )


def get_next_round() -> dict | None:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM next_round ORDER BY id").fetchall()
        if not rows:
            return None
        return {
            "round": rows[0]["round"],
            "matches": [{"date": r["date"], "home": r["home"], "away": r["away"]} for r in rows],
        }


def all_matches() -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM matches ORDER BY id"
        ).fetchall()
