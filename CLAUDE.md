# ABC Braník — Football Results Tracker

## Project goal
Scrape football match results for ABC Braník and maintain an up-to-date league standings table.

## Stack
- Python
- Web scraping: BeautifulSoup / requests (or Selenium if JS rendering needed)
- Data storage: CSV or SQLite
- Output: standings table in terminal or HTML

## Data to collect per match
- Date
- Home team / Away team
- Score (goals home : goals away)

## Standings table columns
- Position, Team, Played, Won, Drawn, Lost, Goals For, Goals Against, Goal Difference, Points

## Scraping rules
- Respect robots.txt
- Add delays between requests to avoid rate limiting
- Cache raw HTML locally to avoid repeated fetches during development

## Code style
- Follow global CLAUDE.md conventions
- Keep scraping logic and table logic in separate modules
