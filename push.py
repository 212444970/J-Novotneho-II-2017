import os
import sys
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import re

RAILWAY_URL = os.environ.get("RAILWAY_URL", "").rstrip("/")
PUSH_SECRET = os.environ.get("PUSH_SECRET", "")

LEAGUES = {
    "liga1": "https://www.fotbal.cz/souteze/turnaje/zapas/27aa1eb4-07e1-4f73-a513-b470cc36b878",
    "liga2": "https://www.fotbal.cz/souteze/turnaje/zapas/b6493972-274a-44a9-ab8e-384fe33580ab",
}


def scrape() -> dict:
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = uc.Chrome(options=options, use_subprocess=True)
    results = {}
    try:
        for league_id, url in LEAGUES.items():
            print(f"  Načítám {league_id}...")
            driver.get(url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.MatchRound-match"))
            )
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            results[league_id] = {
                "matches": _parse_played(soup),
                "next_round": _parse_next_round(soup),
            }
    finally:
        driver.quit()
    return results


def _parse_played(soup):
    matches = []
    for a in soup.select("a.MatchRound-match"):
        score_el = a.find("strong", class_="H4")
        if not score_el:
            continue
        parts = score_el.get_text(strip=True).split(":")
        if len(parts) != 2 or not all(p.strip().isdigit() for p in parts):
            continue
        teams = [s.get_text(strip=True) for s in a.select("span.H7")]
        if len(teams) != 2:
            continue
        matches.append({
            "date": _get_date(a),
            "home": teams[0], "away": teams[1],
            "home_goals": int(parts[0]), "away_goals": int(parts[1]),
        })
    return matches


def _parse_next_round(soup):
    sections = []
    for section in soup.select("section.js-matchRoundSection"):
        label = section.get_text(" ", strip=True).split("Zobrazit")[0].strip()
        m = re.search(r"(\d+)\.\s*kolo", label)
        round_num = int(m.group(1)) if m else None
        all_m = section.select("a.MatchRound-match")
        played = [a for a in all_m if a.find("strong", class_="H4")]
        upcoming = [a for a in all_m if not a.find("strong", class_="H4")]
        sections.append({"label": label, "num": round_num, "played": played, "upcoming": upcoming})
    max_played = max((s["num"] for s in sections if s["played"] and s["num"] is not None), default=None)
    if max_played is None:
        return None
    nxt = next((s for s in sections if s["num"] == max_played + 1), None)
    if not nxt:
        return None
    matches = []
    for a in nxt["upcoming"] + nxt["played"]:
        teams = [s.get_text(strip=True) for s in a.select("span.H7")]
        if len(teams) == 2:
            matches.append({"date": _get_date(a), "home": teams[0], "away": teams[1]})
    return {"round": nxt["label"], "matches": matches} if matches else None


def _get_date(a):
    li = a.find_parent("li", class_="MatchRound")
    if li:
        p = li.find("p")
        if p:
            return p.get_text(strip=True).replace("Datum:", "").strip()
    return ""


def push(data: dict):
    url = f"{RAILWAY_URL}/api/push"
    resp = requests.post(url, json=data, headers={"X-Secret": PUSH_SECRET}, timeout=30)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    if not RAILWAY_URL or not PUSH_SECRET:
        print("Nastav RAILWAY_URL a PUSH_SECRET:")
        print('  $env:RAILWAY_URL = "https://tvoje-app.railway.app"')
        print('  $env:PUSH_SECRET = "tajny-klic"')
        sys.exit(1)

    print("Scrapuji fotbal.cz...")
    data = scrape()
    for lid, d in data.items():
        print(f"  {lid}: {len(d['matches'])} zápasů")

    print("Posílám na Railway...")
    result = push(data)
    print("Hotovo:", result)
