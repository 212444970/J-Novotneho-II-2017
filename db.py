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
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament TEXT NOT NULL DEFAULT 'liga1',
                date       TEXT,
                home       TEXT NOT NULL,
                away       TEXT NOT NULL,
                home_goals INTEGER NOT NULL,
                away_goals INTEGER NOT NULL,
                UNIQUE(tournament, date, home, away)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS next_round (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament TEXT NOT NULL DEFAULT 'liga1',
                round      TEXT,
                date       TEXT,
                home       TEXT NOT NULL,
                away       TEXT NOT NULL
            )
        """)
        # migrate old tables without tournament column
        for col in ("matches", "next_round"):
            try:
                conn.execute(f"ALTER TABLE {col} ADD COLUMN tournament TEXT NOT NULL DEFAULT 'liga1'")
            except Exception:
                pass


def upsert_match(tournament: str, date: str, home: str, away: str,
                 home_goals: int, away_goals: int) -> None:
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO matches (tournament, date, home, away, home_goals, away_goals)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(tournament, date, home, away) DO UPDATE SET
                home_goals = excluded.home_goals,
                away_goals = excluded.away_goals
        """, (tournament, date, home, away, home_goals, away_goals))


def save_next_round(tournament: str, round_label: str, matches: list[dict]) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM next_round WHERE tournament = ?", (tournament,))
        for m in matches:
            conn.execute(
                "INSERT INTO next_round (tournament, round, date, home, away) VALUES (?,?,?,?,?)",
                (tournament, round_label, m["date"], m["home"], m["away"])
            )


def get_next_round(tournament: str) -> dict | None:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM next_round WHERE tournament=? ORDER BY id", (tournament,)
        ).fetchall()
        if not rows:
            return None
        return {
            "round": rows[0]["round"],
            "matches": [{"date": r["date"], "home": r["home"], "away": r["away"]} for r in rows],
        }


def all_matches(tournament: str) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM matches WHERE tournament=? ORDER BY id", (tournament,)
        ).fetchall()
