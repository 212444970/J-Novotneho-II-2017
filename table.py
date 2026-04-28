from collections import defaultdict
from db import all_matches


def build_standings() -> list[dict]:
    teams: dict[str, dict] = defaultdict(lambda: {
        "team": "", "played": 0, "won": 0, "drawn": 0, "lost": 0,
        "gf": 0, "ga": 0, "history": [],
    })

    for m in all_matches():
        h, a, hg, ag = m["home"], m["away"], m["home_goals"], m["away_goals"]
        for team in (h, a):
            teams[team]["team"] = team

        teams[h]["played"] += 1
        teams[h]["gf"] += hg
        teams[h]["ga"] += ag

        teams[a]["played"] += 1
        teams[a]["gf"] += ag
        teams[a]["ga"] += hg

        date = m["date"].replace("Datum:", "").strip()

        if hg > ag:
            teams[h]["won"] += 1
            teams[h]["history"].append({"r": "W", "date": date, "opponent": a, "score": f"{hg}:{ag}"})
            teams[a]["lost"] += 1
            teams[a]["history"].append({"r": "L", "date": date, "opponent": h, "score": f"{hg}:{ag}"})
        elif hg < ag:
            teams[a]["won"] += 1
            teams[a]["history"].append({"r": "W", "date": date, "opponent": h, "score": f"{ag}:{hg}"})
            teams[h]["lost"] += 1
            teams[h]["history"].append({"r": "L", "date": date, "opponent": a, "score": f"{ag}:{hg}"})
        else:
            teams[h]["drawn"] += 1
            teams[h]["history"].append({"r": "D", "date": date, "opponent": a, "score": f"{hg}:{ag}"})
            teams[a]["drawn"] += 1
            teams[a]["history"].append({"r": "D", "date": date, "opponent": h, "score": f"{hg}:{ag}"})

    rows = []
    for t in teams.values():
        t["points"] = t["won"] * 3 + t["drawn"]
        t["gd"] = t["gf"] - t["ga"]
        # last 5, most recent first
        t["form"] = list(reversed(t["history"][-5:]))  # most recent first
        del t["history"]
        rows.append(t)

    rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"]))
    for i, row in enumerate(rows, 1):
        row["pos"] = i
    return rows


def print_standings() -> None:
    rows = build_standings()
    if not rows:
        print("Žádné výsledky v databázi.")
        return

    header = f"{'#':>2}  {'Tým':<30} {'Z':>3} {'V':>3} {'R':>3} {'P':>3} {'GF':>4} {'GA':>4} {'GD':>4} {'B':>4}"
    print(header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r['pos']:>2}  {r['team']:<30} {r['played']:>3} {r['won']:>3} "
            f"{r['drawn']:>3} {r['lost']:>3} {r['gf']:>4} {r['ga']:>4} "
            f"{r['gd']:>4} {r['points']:>4}"
        )
