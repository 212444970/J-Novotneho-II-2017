import os
import re
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from bs4 import BeautifulSoup

LEAGUES = {
    "liga1": "https://www.fotbal.cz/souteze/turnaje/zapas/27aa1eb4-07e1-4f73-a513-b470cc36b878",
    "liga2": "https://www.fotbal.cz/souteze/turnaje/zapas/b6493972-274a-44a9-ab8e-384fe33580ab",
}

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191")

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _get_flaresolverr_cookies() -> list[dict]:
    resp = requests.post(
        f"{FLARESOLVERR_URL}/v1",
        json={"cmd": "request.get", "url": "https://www.fotbal.cz", "maxTimeout": 60000},
        timeout=90,
    )
    if not resp.ok:
        raise RuntimeError(f"FlareSolverr HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"FlareSolverr: {data.get('message')}")
    return data["solution"].get("cookies", [])


def fetch_all() -> dict[str, tuple[list[dict], dict | None, str]]:
    raw_cookies = _get_flaresolverr_cookies()
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        context = browser.new_context(user_agent=_USER_AGENT)

        playwright_cookies = []
        for c in raw_cookies:
            same_site = c.get("sameSite", "Lax")
            if same_site not in ("Strict", "Lax", "None"):
                same_site = "Lax"
            playwright_cookies.append({
                "name": c["name"],
                "value": c["value"],
                "domain": c.get("domain", ".fotbal.cz"),
                "path": c.get("path", "/"),
                "secure": bool(c.get("secure", False)),
                "httpOnly": bool(c.get("httpOnly", False)),
                "sameSite": same_site,
            })
        if playwright_cookies:
            context.add_cookies(playwright_cookies)

        page = context.new_page()
        stealth_sync(page)

        for league_id, url in LEAGUES.items():
            page.goto(url, wait_until="load", timeout=60000)
            page.wait_for_timeout(8000)
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.get_text(strip=True) if soup.title else "no title"
            matches_found = len(soup.select("a.MatchRound-match"))
            if matches_found == 0:
                raise RuntimeError(
                    f"No matches on {league_id}. Title: '{title}'. First 300: {html[:300]}"
                )
            title = title.split("|")[0].strip()
            results[league_id] = (_parse_played(soup), _parse_next_round(soup), title)

        browser.close()

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
