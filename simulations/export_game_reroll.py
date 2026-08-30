"""
Exports one real match's shots, in minute order, alongside a single
deterministic re-simulation of that same match -- every shot re-rolled as
an independent Bernoulli(xG) trial, exactly the same model the rest of the
site's 1,000,000-sim treemap uses, just applied to one match's shots one
time rather than in bulk. Feeds the "re-roll one game" section of
pl-xg-simulator.html: a shot-by-shot pitch replay showing the real
Understat outcome alongside this one simulated alternate universe for the
same match.

Not part of the big pass / champions.bin universe -- this is a standalone,
illustrative single draw, seeded independently (GAME_REROLL_SEED below),
not sim number N of the 1,000,000. Own goals aren't specially modelled,
same simplification as the rest of the site (see simulate_season.py's own
module docstring) -- moot here anyway, since the chosen match has none.

Usage:
    python export_game_reroll.py --shots data/shots_2025_26.csv \
        --home "Manchester United" --away "Bournemouth" \
        --out ../articles/pl-treemap-data/game-reroll-data.json
"""

import argparse
import json
import sys

import numpy as np

from simulate_season import load_shots

# Fixed, dedicated seed for this one illustrative re-roll -- independent of
# the big pass's own seed (this match isn't sim number N of the 1,000,000;
# it's a standalone single draw), but fixed so the page shows the same
# "alternate universe" on every visit rather than reshuffling per load.
GAME_REROLL_SEED = 20260051


def main():
    parser = argparse.ArgumentParser(description="Export one match's real shots + a single re-roll")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--home", required=True, help="Home team name, exactly as in the shots CSV")
    parser.add_argument("--away", required=True, help="Away team name, exactly as in the shots CSV")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    shots = load_shots(args.shots)
    m = shots[(shots["h_team"] == args.home) & (shots["a_team"] == args.away)]
    if m.empty:
        raise SystemExit(f"no shots found for {args.home} vs {args.away} -- check team names/args.shots")
    match_id = int(m["match_id"].iloc[0])
    m = m.sort_values("minute", kind="stable").reset_index(drop=True)
    print(f"{args.home} vs {args.away} (match_id {match_id}): {len(m)} shots", file=sys.stderr)

    rng = np.random.default_rng(GAME_REROLL_SEED)
    sim_scored = rng.random(len(m)) < m["xG"].to_numpy(dtype=float)

    shots_out = []
    real_h = real_a = sim_h = sim_a = 0
    for i, row in m.iterrows():
        is_home = row["h_a"] == "h"
        real_goal = row["result"] == "Goal"
        if real_goal:
            if is_home:
                real_h += 1
            else:
                real_a += 1
        sim_goal = bool(sim_scored[i])
        if sim_goal:
            if is_home:
                sim_h += 1
            else:
                sim_a += 1

        shots_out.append({
            "minute": int(row["minute"]),
            "player": row["player"],
            "team": row["h_team"] if is_home else row["a_team"],
            "is_home": bool(is_home),
            # Understat's X/Y are normalised 0..1 from the SHOOTING side's
            # own attacking perspective (always toward X=1) -- the frontend
            # mirrors an away shot's X/Y so both sides plot correctly onto
            # one continuous pitch.
            "x": float(row["X"]), "y": float(row["Y"]),
            "xg": round(float(row["xG"]), 3),
            "real_result": row["result"],
            "real_goal": bool(real_goal),
            "sim_goal": sim_goal,
            "real_score": [int(real_h), int(real_a)],
            "sim_score": [int(sim_h), int(sim_a)],
        })

    payload = {
        "match_id": match_id,
        "home_team": args.home,
        "away_team": args.away,
        "date": str(m["date"].iloc[0]) if "date" in m.columns else None,
        "real_final_score": [int(real_h), int(real_a)],
        "sim_final_score": [int(sim_h), int(sim_a)],
        "shots": shots_out,
    }

    with open(args.out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {len(shots_out)} shots to {args.out}", file=sys.stderr)
    print(f"Real: {args.home} {real_h}-{real_a} {args.away}", file=sys.stderr)
    print(f"Sim:  {args.home} {sim_h}-{sim_a} {args.away}", file=sys.stderr)


if __name__ == "__main__":
    main()
