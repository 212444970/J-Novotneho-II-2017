import os
import re
import time
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

LEAGUES = {
    "liga1": "https://www.fotbal.cz/souteze/turnaje/zapas/27aa1eb4-07e1-4f73-a513-b470cc36b878",
    "liga2": "https://www.fotbal.cz/souteze/turnaje/zapas/b6493972-274a-44a9-ab8e-384fe33580ab",
}

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191")
_ON_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT"))

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
)


def _get_cf_clearance() -> str:
    """Use FlareSolverr to get a valid cf_clearance cookie."""
    resp = requests.post(
        f"{FLARESOLVERR_URL}/v1",
        json={"cmd": "request.get", "url": "https://www.fotbal.cz", "maxTimeout": 60000},
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"FlareSolverr: {data.get('message')}")
    cookies = {c["name"]: c["value"] for c in data["solution"].get("cookies", [])}
    cf = cookies.get("cf_clearance", "")
    if not cf:
        raise RuntimeError("cf_clearance cookie not found in FlareSolverr response")
    return cf


def _make_driver(cf_clearance: str):
    if _ON_RAILWAY:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        opts = webdriver.ChromeOptions()
        opts.binary_location = "/usr/bin/chromium"
        for arg in (
            f"--user-agent={_USER_AGENT}",
            "--window-size=1920,1080",
            "--headless=new",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--no-zygote",
        ):
            opts.add_argument(arg)
        driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=opts)
    else:
        options = uc.ChromeOptions()
        options.add_argument(f"--user-agent={_USER_AGENT}")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = uc.Chrome(options=options, use_subprocess=True, version_main=147)

    driver.get("https://www.fotbal.cz")
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    driver.add_cookie({"name": "cf_clearance", "value": cf_clearance,
                       "domain": ".fotbal.cz", "path": "/", "secure": True})
    return driver


def fetch_all() -> dict[str, tuple[list[dict], dict | None, str]]:
    cf = _get_cf_clearance()
    driver = _make_driver(cf)
    results = {}
    try:
        for league_id, url in LEAGUES.items():
            driver.get(url)
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "a.MatchRound-match"))
            )
            time.sleep(2)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            title = soup.title.get_text(strip=True).split("|")[0].strip() if soup.title else league_id
            results[league_id] = (_parse_played(soup), _parse_next_round(soup), title)
    finally:
        driver.quit()
    return results


def _parse_played(soup: BeautifulSoup) -> list[dict]:
    matches = []
    for a in soup.select("a.MatchRound-match"):
        score_el = a.find("strong", class_="H4")
        if not score_el or not _is_score(score_el.get_text(strip=True)):
            continue
        score = score_el.get_text(strip=True)
        teams = [s.get_text(strip=True) for s in a.select("span.H7")]
        if len(teams) != 2:
            continue
        matches.append({"date": _get_date(a), "home": teams[0], "away": teams[1], "score": score})
    return matches


def _parse_next_round(soup: BeautifulSoup) -> dict | None:
    sections = []
    for section in soup.select("section.js-matchRoundSection"):
        label = section.get_text(" ", strip=True).split("Zobrazit")[0].strip()
        m = re.search(r"(\d+)\.\s*kolo", label)
        round_num = int(m.group(1)) if m else None
        all_matches = section.select("a.MatchRound-match")
        played = [a for a in all_matches if a.find("strong", class_="H4")]
        upcoming = [a for a in all_matches if not a.find("strong", class_="H4")]
        sections.append({"label": label, "num": round_num, "played": played, "upcoming": upcoming})

    max_played_round = max(
        (s["num"] for s in sections if s["played"] and s["num"] is not None),
        default=None,
    )
    if max_played_round is None:
        return None

    next_section = next((s for s in sections if s["num"] == max_played_round + 1), None)
    if not next_section:
        return None

    matches = []
    for a in next_section["upcoming"] + next_section["played"]:
        teams = [s.get_text(strip=True) for s in a.select("span.H7")]
        if len(teams) != 2:
            continue
        matches.append({"date": _get_date(a), "home": teams[0], "away": teams[1]})

    return {"round": next_section["label"], "matches": matches} if matches else None


def _get_date(a) -> str:
    li = a.find_parent("li", class_="MatchRound")
    if li:
        p = li.find("p")
        if p:
            return p.get_text(strip=True).replace("Datum:", "").strip()
    return ""


def _is_score(text: str) -> bool:
    parts = text.split(":")
    if len(parts) != 2:
        return False
    return all(p.strip().isdigit() for p in parts)
