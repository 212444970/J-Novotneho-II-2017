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
    app.run(debug=True)
