import os
from datetime import datetime
from flask import Flask, render_template
from db import init_db, DB_PATH
from table import build_standings

app = Flask(__name__)

SOURCE_URL = "https://www.fotbal.cz/souteze/turnaje/hlavni/27aa1eb4-07e1-4f73-a513-b470cc36b878"


@app.route("/")
def index():
    init_db()
    rows = build_standings()
    mtime = os.path.getmtime(DB_PATH)
    updated = datetime.fromtimestamp(mtime).strftime("%-d. %-m. %Y %H:%M")
    return render_template("index.html", rows=rows, source_url=SOURCE_URL, updated=updated)


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
