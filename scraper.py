import os
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

LEAGUES = {
    "liga1": "https://www.fotbal.cz/souteze/turnaje/zapas/27aa1eb4-07e1-4f73-a513-b470cc36b878",
    "liga2": "https://www.fotbal.cz/souteze/turnaje/zapas/b6493972-274a-44a9-ab8e-384fe33580ab",
}

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36"
)

# Reads from env var CF_CLEARANCE (Railway) or falls back to hardcoded value (local)
_CF_CLEARANCE_FALLBACK = (
    "Xxfkw4NesscagWZzV8wg61Fg8a85LQg4wmEXo.73RJw-1777234006-1.2.1.1-"
    "8kIeeHRDVViTRZylYd2UvsUL9IIAgxHICPrfcMc.w.tGZCFDJl.7kBe9M_QEAcl"
    "FsZf.PWnt_D1pQcr8FwCKIgjwLLYdMydMWQYkE8OoTgy3FuFP.r_wzKmphPjvaEf"
    "JGks2V1qh5Zdko84Ln6mxvbN6VjAnQCn6MwUGBBxT5Qoc16LEV0biiIO7_qsh17a"
    "UcEcw_ll.pgK.VdPYLxuygpGjJ19uEC6GKsWbgR7WAdF_Qu6z4jDUAUcYgvn.a6t"
    "9Z9..jeh0XubsnAv23.sDUa7NWDaStDPwjJM8L75fPFAxfL3OuCdg.szr9rQamOF9"
    "3cfCY.UVvmpAeWsb0INYDrRblhSgriEJLkdip0rRLeiC0_Ew_VmUGjq_lSFt3YzBE"
    "lTgpXuO7HCJDEua41JgE3aGkXoTw7HvlrEniV_ohq4"
)

_ON_RAILWAY = bool(os.environ.get("RAILWAY_ENVIRONMENT"))


def _get_cf_clearance() -> str:
    return os.environ.get("CF_CLEARANCE", _CF_CLEARANCE_FALLBACK)


def _make_driver() -> uc.Chrome:
    options = uc.ChromeOptions()
    options.add_argument(f"--user-agent={_USER_AGENT}")
    options.add_argument("--window-size=1920,1080")
    if _ON_RAILWAY:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.binary_location = "/usr/bin/google-chrome"
        return uc.Chrome(options=options, use_subprocess=False)
    return uc.Chrome(options=options, use_subprocess=True, version_main=147)


def fetch_all() -> dict[str, tuple[list[dict], dict | None, str]]:
    """Returns {league_id: (played_matches, next_round, page_title)}"""
    driver = _make_driver()
    results = {}
    try:
        driver.get("https://www.fotbal.cz")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        driver.add_cookie({"name": "cf_clearance", "value": _get_cf_clearance(),
                           "domain": ".fotbal.cz", "path": "/", "secure": True})

        for league_id, url in LEAGUES.items():
            driver.get(url)
            WebDriverWait(driver, 20).until(
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
    import re

    # collect all sections with their round number and matches
    sections = []
    for section in soup.select("section.js-matchRoundSection"):
        label = section.get_text(" ", strip=True).split("Zobrazit")[0].strip()
        m = re.search(r"(\d+)\.\s*kolo", label)
        round_num = int(m.group(1)) if m else None
        all_matches = section.select("a.MatchRound-match")
        played = [a for a in all_matches if a.find("strong", class_="H4")]
        upcoming = [a for a in all_matches if not a.find("strong", class_="H4")]
        sections.append({"label": label, "num": round_num, "played": played, "upcoming": upcoming})

    # find highest round number that has at least one played match
    max_played_round = max(
        (s["num"] for s in sections if s["played"] and s["num"] is not None),
        default=None,
    )
    if max_played_round is None:
        return None

    # find the section with round number = max_played_round + 1
    next_num = max_played_round + 1
    next_section = next((s for s in sections if s["num"] == next_num), None)
    if not next_section:
        return None

    matches = []
    for a in next_section["upcoming"] + next_section["played"]:
        teams = [s.get_text(strip=True) for s in a.select("span.H7")]
        if len(teams) != 2:
            continue
        matches.append({"date": _get_date(a), "home": teams[0], "away": teams[1]})

    if not matches:
        return None
    return {"round": next_section["label"], "matches": matches}


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
