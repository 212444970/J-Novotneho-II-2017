import os
import re
import requests
from bs4 import BeautifulSoup

LEAGUES = {
    "liga1": "https://www.fotbal.cz/souteze/turnaje/zapas/27aa1eb4-07e1-4f73-a513-b470cc36b878",
    "liga2": "https://www.fotbal.cz/souteze/turnaje/zapas/b6493972-274a-44a9-ab8e-384fe33580ab",
}

# Set FLARESOLVERR_URL as Railway env var, e.g. http://flaresolverr:8191
FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191")


def _fetch_html(url: str) -> str:
    resp = requests.post(
        f"{FLARESOLVERR_URL}/v1",
        json={"cmd": "request.get", "url": url, "maxTimeout": 60000},
        timeout=90,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"FlareSolverr error: {data.get('message')}")
    return data["solution"]["response"]


def fetch_all() -> dict[str, tuple[list[dict], dict | None, str]]:
    results = {}
    for league_id, url in LEAGUES.items():
        html = _fetch_html(url)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text(strip=True).split("|")[0].strip() if soup.title else league_id
        results[league_id] = (_parse_played(soup), _parse_next_round(soup), title)
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
