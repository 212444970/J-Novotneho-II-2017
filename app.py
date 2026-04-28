import os
from datetime import datetime
from flask import Flask, render_template
from db import init_db, DB_PATH, get_next_round
from table import build_standings

app = Flask(__name__)

LEAGUES_META = {
    "liga1": {
        "name": "J. Novotného II",
        "source": "https://www.fotbal.cz/souteze/turnaje/hlavni/27aa1eb4-07e1-4f73-a513-b470cc36b878",
    },
    "liga2": {
        "name": "2025 H3O – H3O 2017/18",
        "source": "https://www.fotbal.cz/souteze/turnaje/hlavni/b6493972-274a-44a9-ab8e-384fe33580ab",
    },
}


@app.route("/")
def index():
    init_db()
    mtime = os.path.getmtime(DB_PATH)
    dt = datetime.fromtimestamp(mtime)
    updated = f"{dt.day}. {dt.month}. {dt.year} {dt.strftime('%H:%M')}"
    leagues = []
    for lid, meta in LEAGUES_META.items():
        leagues.append({
            "id": lid,
            "name": meta["name"],
            "standings": {v: build_standings(lid, v) for v in ("all", "home", "away")},
            "next_round": get_next_round(lid),
            "source_url": meta["source"],
        })
    return render_template("index.html", leagues=leagues, updated=updated)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
