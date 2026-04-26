from flask import Flask, render_template
from db import init_db
from table import build_standings

app = Flask(__name__)


@app.route("/")
def index():
    init_db()
    rows = build_standings()
    return render_template("index.html", rows=rows)


if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
