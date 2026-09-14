"""
Real-life expected-goals-for/against per team, aggregated across the whole
real 2025/26 season from the shots CSV -- feeds the "real-life GD vs.
expected GD" comparisons on a handful of roster-card highlights (e.g.
Tottenham, Wolves, Burnley). Purely real-world arithmetic, no simulation
involved, so -- unlike touching export_treemap_data.py's own pipeline --
regenerating this carries none of the RNG-tie-break nondeterminism risk
flagged elsewhere in this codebase's history; it's a small, standalone,
fully deterministic pass kept separate so the main pipeline's own outputs
never need to be re-run just to add this.

Usage:
    python export_real_xg_table.py --shots data/shots_2025_26.csv \
        --out ../articles/pl-treemap-data/real-xg-table.json
"""

import argparse
import json

from simulate_season import build_real_table, load_shots


def main():
    parser = argparse.ArgumentParser(description="Export real per-team xG-for/xG-against totals")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    shots = load_shots(args.shots)
    real_table = build_real_table(shots)

    matches = shots.drop_duplicates("match_id")[["match_id", "h_team", "a_team"]].set_index("match_id")
    xg_h = shots[shots["h_a"] == "h"].groupby("match_id")["xG"].sum()
    xg_a = shots[shots["h_a"] == "a"].groupby("match_id")["xG"].sum()
    matches["xg_h"] = xg_h
    matches["xg_a"] = xg_a
    matches = matches.fillna(0.0)

    xg_for, xg_against = {}, {}
    for _, m in matches.iterrows():
        h, a = m["h_team"], m["a_team"]
        xg_for[h] = xg_for.get(h, 0.0) + m["xg_h"]
        xg_against[h] = xg_against.get(h, 0.0) + m["xg_a"]
        xg_for[a] = xg_for.get(a, 0.0) + m["xg_a"]
        xg_against[a] = xg_against.get(a, 0.0) + m["xg_h"]

    out = []
    for _, row in real_table.iterrows():
        team = row["team"]
        xgf, xga = xg_for[team], xg_against[team]
        out.append({
            "team": team,
            "position": int(row["position"]),
            "gd": int(row["gd"]),
            "xgf": round(float(xgf), 2),
            "xga": round(float(xga), 2),
            "xgd": round(float(xgf - xga), 2),
        })

    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {len(out)} teams to {args.out}")


if __name__ == "__main__":
    main()
