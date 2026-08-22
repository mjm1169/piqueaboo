"""
Export a compact JSON of shot data for the browser-side simulator on the
article page. The full scraped CSV carries a lot of columns/precision the
client doesn't need (result type, X/Y coordinates, situation, etc.) - this
keeps just what the in-browser Monte Carlo re-run needs: per match, the
home/away team, and each shot's xG + scoring player.

Usage:
    python export_client_data.py --shots data/shots_2024_25.csv \
        --out ../articles/pl-xg-simulator-data.json
"""

import argparse
import json

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Export slim shot data for the client-side simulator")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.shots)
    df["xG"] = pd.to_numeric(df["xG"], errors="coerce").fillna(0.0).clip(0, 1)

    teams = sorted(set(df["h_team"]) | set(df["a_team"]))
    team_idx = {t: i for i, t in enumerate(teams)}

    matches = []
    for match_id, g in df.groupby("match_id", sort=False):
        h = g[g["h_a"] == "h"]
        a = g[g["h_a"] == "a"]
        matches.append({
            "h": team_idx[g["h_team"].iloc[0]],
            "a": team_idx[g["a_team"].iloc[0]],
            "date": str(g["date"].iloc[0])[:10],
            "hg": int(g["h_goals"].iloc[0]),   # real result, for "vs reality" comparisons
            "ag": int(g["a_goals"].iloc[0]),
            "xh": [round(float(x), 4) for x in h["xG"]],
            "ph": h["player"].tolist(),
            "xa": [round(float(x), 4) for x in a["xG"]],
            "pa": a["player"].tolist(),
        })

    # Keep matches in chronological order (nicer if ever displayed as a fixture list)
    matches.sort(key=lambda m: m["date"])

    payload = {"teams": teams, "matches": matches}
    with open(args.out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))

    import os
    size_kb = os.path.getsize(args.out) / 1024
    print(f"Wrote {len(matches)} matches, {len(teams)} teams to {args.out} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
