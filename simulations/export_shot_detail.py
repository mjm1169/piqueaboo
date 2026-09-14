"""
Regenerates one real match's full shot-by-shot detail (xG, real Understat
result, and this one sim's own re-rolled outcome) for a SPECIFIC sim number
already flagged in flagged-games.json -- the "list out all the shots" level
of detail flagged-games.json itself doesn't keep (it only retains an ordered
scorer list, not every shot including misses).

Uses the exact same per-match RNG scheme as the big pass
(_match_rng(seed, match_index), full (n_sims, ...) shape) so the regenerated
sim bit-for-bit matches champions.bin/flagged-games.json's own record for
that sim -- see export_treemap_data.py's build_campaign_for_sim docstring
for why a truncated shape would silently regenerate the wrong season.

Usage:
    python export_shot_detail.py --shots data/shots_2025_26.csv \
        --home "Crystal Palace" --away "Bournemouth" --sim 509023 \
        --out ../articles/pl-treemap-data/mateta-shot-detail.json
"""

import argparse
import json
import sys

import numpy as np

from simulate_season import build_match_index, load_shots

BIG_PASS_SEED = 20252026
BIG_PASS_N_SIMS = 1_000_000


def _match_rng(seed, match_index):
    return np.random.default_rng(np.random.SeedSequence([seed, match_index]))


def main():
    parser = argparse.ArgumentParser(description="Export one flagged sim's full shot-by-shot detail for one match")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--home", required=True)
    parser.add_argument("--away", required=True)
    parser.add_argument("--sim", type=int, required=True)
    parser.add_argument("--seed", type=int, default=BIG_PASS_SEED)
    parser.add_argument("--n-sims", type=int, default=BIG_PASS_N_SIMS)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    shots = load_shots(args.shots)
    matches = build_match_index(shots)
    match_i = next(
        (i for i, m in enumerate(matches) if m["home_team"] == args.home and m["away_team"] == args.away),
        None,
    )
    if match_i is None:
        raise SystemExit(f"no match found for {args.home} vs {args.away} -- check team names")
    m = matches[match_i]
    print(f"{args.home} vs {args.away} (match_id {m['match_id']}, index {match_i}): "
          f"{len(m['xg_h'])} home shots, {len(m['xg_a'])} away shots", file=sys.stderr)

    rng_i = _match_rng(args.seed, match_i)
    draws_h = rng_i.random((args.n_sims, len(m["xg_h"]))) < m["xg_h"] if len(m["xg_h"]) else np.zeros((args.n_sims, 0), dtype=bool)
    draws_a = rng_i.random((args.n_sims, len(m["xg_a"]))) < m["xg_a"] if len(m["xg_a"]) else np.zeros((args.n_sims, 0), dtype=bool)
    sim_h_row = draws_h[args.sim]
    sim_a_row = draws_a[args.sim]

    # Real per-shot data (result/minute), pulled in the same filtered order
    # build_match_index used (h_a split, original CSV row order preserved --
    # groupby(..., sort=False) then a plain boolean filter, no re-sort).
    real = shots[shots["match_id"] == m["match_id"]]
    real_h = real[real["h_a"] == "h"].reset_index(drop=True)
    real_a = real[real["h_a"] == "a"].reset_index(drop=True)
    assert len(real_h) == len(m["xg_h"]) and len(real_a) == len(m["xg_a"]), \
        "shot count mismatch between build_match_index and a direct CSV filter"

    shots_out = []
    for side, real_side, draws_row, xg_arr, players, minutes, is_pen, team, opp in (
        ("h", real_h, sim_h_row, m["xg_h"], m["players_h"], m["minutes_h"], m["is_pen_h"], args.home, args.away),
        ("a", real_a, sim_a_row, m["xg_a"], m["players_a"], m["minutes_a"], m["is_pen_a"], args.away, args.home),
    ):
        for j in range(len(xg_arr)):
            row = real_side.iloc[j]
            shots_out.append({
                "minute": int(minutes[j]),
                "player": str(players[j]),
                "team": team,
                "is_home": side == "h",
                "penalty": bool(is_pen[j]) if is_pen is not None else False,
                "xg": round(float(xg_arr[j]), 3),
                "real_result": str(row["result"]),
                "real_goal": bool(row["result"] == "Goal"),
                "sim_goal": bool(draws_row[j]),
            })

    shots_out.sort(key=lambda s: s["minute"])
    real_h_goals = sum(1 for s in shots_out if s["is_home"] and s["real_goal"])
    real_a_goals = sum(1 for s in shots_out if not s["is_home"] and s["real_goal"])
    sim_h_goals = int(sim_h_row.sum())
    sim_a_goals = int(sim_a_row.sum())

    # Running score, once sorted into minute order (matches game-reroll's
    # own convention of a per-shot running scoreline).
    real_h_run = real_a_run = sim_h_run = sim_a_run = 0
    for s in shots_out:
        if s["real_goal"]:
            if s["is_home"]:
                real_h_run += 1
            else:
                real_a_run += 1
        if s["sim_goal"]:
            if s["is_home"]:
                sim_h_run += 1
            else:
                sim_a_run += 1
        s["real_score"] = [real_h_run, real_a_run]
        s["sim_score"] = [sim_h_run, sim_a_run]

    payload = {
        "sim": args.sim,
        "match_id": int(m["match_id"]),
        "home_team": args.home,
        "away_team": args.away,
        "date": m["date"],
        "real_final_score": [real_h_goals, real_a_goals],
        "sim_final_score": [sim_h_goals, sim_a_goals],
        "shots": shots_out,
    }

    with open(args.out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {len(shots_out)} shots to {args.out}", file=sys.stderr)
    print(f"Real: {args.home} {real_h_goals}-{real_a_goals} {args.away}", file=sys.stderr)
    print(f"Sim:  {args.home} {sim_h_goals}-{sim_a_goals} {args.away} (sim #{args.sim})", file=sys.stderr)


if __name__ == "__main__":
    main()
