"""
Scrape shot-by-shot xG data for a full season from Understat.

Understat used to embed match/league data as JSON strings inside <script>
tags on the page (a `var shotsData = JSON.parse('...')` pattern). As of
2026 the site instead fetches this data client-side via a couple of small
JSON endpoints once the page has loaded, so this script talks to those
endpoints directly:

  1. GET /getLeagueData/{league}/{season} -> list of played matches for
     the season (their match ids), plus season-level team/player summaries
     we don't need here.
  2. GET /getMatchData/{match_id} -> shot-by-shot data for both teams in
     one match, each shot including its xG.
  3. Combine everything into one DataFrame / CSV, one row per shot.

Usage:
    python scrape_understat_shots.py --league EPL --season 2024 --out shots_2024_25.csv

Notes:
  - "season 2024" on Understat means the 2024/25 season (labelled by start year).
  - League codes: EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL
  - Adds a short delay between requests and reuses one session - be polite,
    and check Understat's terms of use before scraping at scale/frequency.
  - Each shot row includes: id, minute, result, X, Y, xG, player, h_a,
    player_id, situation, shotType, match_id, home_team, away_team, date.
"""

import argparse
import sys
import time

import pandas as pd
import requests

BASE_URL = "https://understat.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; personal-research-script/1.0)",
    "X-Requested-With": "XMLHttpRequest",
}


def get_season_matches(league: str, season: str, session: requests.Session) -> list[dict]:
    """Return played matches for a league/season, e.g. league='EPL', season='2024'."""
    url = f"{BASE_URL}/getLeagueData/{league}/{season}"
    headers = {**HEADERS, "Referer": f"{BASE_URL}/league/{league}/{season}"}
    resp = session.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    payload = resp.json()
    return [m for m in payload["dates"] if m.get("isResult")]


def get_match_shots(match_id: str, session: requests.Session) -> pd.DataFrame:
    """Return a DataFrame of every shot (both teams) in one match, with xG."""
    url = f"{BASE_URL}/getMatchData/{match_id}"
    headers = {**HEADERS, "Referer": f"{BASE_URL}/match/{match_id}"}
    resp = session.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    payload = resp.json()
    shots_data = payload.get("shots", {})  # {'h': [...], 'a': [...]}

    rows = []
    for side in ("h", "a"):
        rows.extend(shots_data.get(side, []))

    df = pd.DataFrame(rows)
    if not df.empty:
        # xG etc. arrive as strings in the raw JSON - coerce the numeric ones
        for col in ("xG", "minute", "X", "Y"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["match_id"] = match_id
    return df


def scrape_season(league: str, season: str, delay: float = 1.0) -> pd.DataFrame:
    session = requests.Session()
    matches = get_season_matches(league, season, session)
    print(f"Found {len(matches)} played matches for {league} {season}", file=sys.stderr)

    all_shots = []
    for i, m in enumerate(matches, 1):
        match_id = m["id"]
        home, away = m["h"]["title"], m["a"]["title"]
        print(f"[{i}/{len(matches)}] {home} vs {away} (match_id={match_id})", file=sys.stderr)

        try:
            shots = get_match_shots(match_id, session)
        except Exception as exc:
            print(f"  failed: {exc}", file=sys.stderr)
            continue

        if not shots.empty:
            shots["home_team"] = home
            shots["away_team"] = away
            shots["date"] = m.get("datetime")
            all_shots.append(shots)

        time.sleep(delay)

    if not all_shots:
        return pd.DataFrame()

    return pd.concat(all_shots, ignore_index=True)


def main():
    parser = argparse.ArgumentParser(description="Scrape shot-by-shot xG data from Understat")
    parser.add_argument("--league", default="EPL", help="EPL, La_liga, Bundesliga, Serie_A, Ligue_1, RFPL")
    parser.add_argument("--season", default="2024", help="Season start year, e.g. 2024 for 2024/25")
    parser.add_argument("--out", default="shots.csv", help="Output CSV path")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between match requests")
    args = parser.parse_args()

    df = scrape_season(args.league, args.season, delay=args.delay)
    if df.empty:
        print("No shot data collected.", file=sys.stderr)
        sys.exit(1)

    df.to_csv(args.out, index=False)
    print(f"Saved {len(df)} shots to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
