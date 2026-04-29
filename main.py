import sys
from db import init_db, upsert_match, save_next_round
from scraper import fetch_all
from table import print_standings


def _parse_score(score: str) -> tuple[int, int] | None:
    parts = score.split(":")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        return None


def scrape_and_store() -> None:
    print("Načítám výsledky z fotbal.cz ...")
    all_data = fetch_all()
    for league_id, (played, next_round, title) in all_data.items():
        saved = skipped = 0
        for m in played:
            parsed = _parse_score(m.get("score", ""))
            if not parsed:
                skipped += 1
                continue
            upsert_match(league_id, m["date"], m["home"], m["away"], *parsed)
            saved += 1
        print(f"[{league_id}] {title}: {saved} zápasů uloženo, {skipped} přeskočeno.")
        if next_round:
            save_next_round(league_id, next_round["round"], next_round["matches"])
            print(f"[{league_id}] Příští kolo: {next_round['round']} ({len(next_round['matches'])} zápasů)")


def main() -> None:
    init_db()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "scrape":
        scrape_and_store()
    elif cmd == "table":
        print_standings("liga1")
        print_standings("liga2")
    else:
        scrape_and_store()
        print_standings("liga1")
        print_standings("liga2")


if __name__ == "__main__":
    main()
