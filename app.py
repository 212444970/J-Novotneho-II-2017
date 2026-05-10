import os
import hmac
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from db import init_db, get_next_round, get_last_updated, upsert_match, save_next_round, set_last_updated
from table import build_standings

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "branik-dev")

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
    updated = get_last_updated()
    leagues = []
    for lid, meta in LEAGUES_META.items():
        leagues.append({
            "id": lid,
            "name": meta["name"],
            "standings": {v: build_standings(lid, v) for v in ("all", "home", "away")},
            "next_round": get_next_round(lid),
            "source_url": meta["source"],
        })
    messages = flash_messages()
    return render_template("index.html", leagues=leagues, updated=updated, messages=messages)


@app.route("/api/push", methods=["POST"])
def api_push():
    secret = os.environ.get("PUSH_SECRET", "")
    token = request.headers.get("X-Secret", "")
    if not secret or not hmac.compare_digest(token, secret):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(force=True)
    if not data:
        return jsonify({"error": "no data"}), 400
    init_db()
    summary = []
    for league_id, league_data in data.items():
        for m in league_data.get("matches", []):
            upsert_match(league_id, m["date"], m["home"], m["away"], m["home_goals"], m["away_goals"])
        nr = league_data.get("next_round")
        if nr:
            save_next_round(league_id, nr["round"], nr["matches"])
        summary.append(f"{league_id}: {len(league_data.get('matches', []))} zápasů")
    set_last_updated()
    return jsonify({"ok": True, "summary": ", ".join(summary)})


@app.route("/debug")
def debug():
    import traceback
    try:
        from scraper import _get_cf_clearance, LEAGUES
        from playwright.sync_api import sync_playwright
        from bs4 import BeautifulSoup
        cf, user_agent = _get_cf_clearance()
        url = list(LEAGUES.values())[0]
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--no-zygote", "--disable-extensions"])
            context = browser.new_context(user_agent=user_agent)
            context.add_cookies([{"name": "cf_clearance", "value": cf, "domain": ".fotbal.cz", "path": "/", "secure": True, "httpOnly": False, "sameSite": "None"}])
            page = context.new_page()
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_timeout(5000)
            html = page.content()
            browser.close()
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text() if soup.title else "no title"
        matches = len(soup.select("a.MatchRound-match"))
        return f"<pre>Title: {title}\nMatchRound-match count: {matches}\n\nFirst 3000 chars:\n{html[:3000]}</pre>"
    except Exception:
        return f"<pre>{traceback.format_exc()}</pre>", 500


@app.route("/refresh", methods=["POST"])
def refresh():
    try:
        from main import scrape_and_store
        info = scrape_and_store()
        flash(f"ok:{info}")
    except Exception as e:
        flash(f"err:{e}")
    return redirect(url_for("index"))


def flash_messages():
    from flask import get_flashed_messages
    return get_flashed_messages()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
