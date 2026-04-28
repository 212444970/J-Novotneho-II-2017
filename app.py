import os
from datetime import datetime
from flask import Flask, render_template
from db import init_db, DB_PATH, get_next_round
from table import build_standings

app = Flask(__name__)

SOURCES = {
    "liga1": "https://www.fotbal.cz/souteze/turnaje/hlavni/27aa1eb4-07e1-4f73-a513-b470cc36b878",
    "liga2": "https://www.fotbal.cz/souteze/turnaje/hlavni/b6493972-274a-44a9-ab8e-384fe33580ab",
}


@app.route("/")
def index():
    init_db()
    mtime = os.path.getmtime(DB_PATH)
    updated = datetime.fromtimestamp(mtime).strftime("%-d. %-m. %Y %H:%M")
    leagues = []
    for lid, source_url in SOURCES.items():
        leagues.append({
            "id": lid,
            "rows": build_standings(lid),
            "next_round": get_next_round(lid),
            "source_url": source_url,
        })
    return render_template("index.html", leagues=leagues, updated=updated)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
