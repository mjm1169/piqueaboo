"""
Exports one real match's shots, in minute order, alongside a single
deterministic re-simulation of that same match -- every shot re-rolled as
an independent Bernoulli(xG) trial, exactly the same model the rest of the
site's 1,000,000-sim treemap uses, just applied to one match's shots one
time rather than in bulk. Feeds the "re-roll one game" section of
pl-xg-simulator.html: a shot-by-shot pitch replay showing the real
Understat outcome alongside this one simulated alternate universe for the
same match.

This IS sim number N of the 1,000,000: it regenerates the match with the
big pass's own per-match RNG (_match_rng(seed, match_index), full
(n_sims, ...) shape), so the shot-by-shot replay shown here is bit-for-bit
the same match that sim N plays in champions.bin and everywhere else on the
page -- which is what lets the article name a real simulation number.
See export_treemap_data.py's build_campaign_for_sim docstring for why a
truncated draw shape would silently regenerate the wrong match.

Own goals aren't specially modelled, same simplification as the rest of the
site (see simulate_season.py's own module docstring) -- moot here anyway,
since the chosen match has none.

Usage:
    python export_game_reroll.py --shots data/shots_2025_26.csv \
        --home "Liverpool" --away "Bournemouth" --sim 10917 \
        --out ../articles/pl-treemap-data/game-reroll-data.json

Match choice: originally Man Utd 4-4 Bournemouth (39 shots), then swapped to
Newcastle 2-3 Liverpool (15 shots) after mobile feedback that the first pick
was too dense for a small screen. Swapped again, per an explicit request
that this section show the season's own opening fixture: Liverpool 4-2
Bournemouth (2025-08-15, 29 shots -- close to the CSV-wide median of 25, not
the deliberately-light pick the previous match was).
"""

import argparse
import json
import sys

import numpy as np

from simulate_season import build_match_index, load_shots

BIG_PASS_SEED = 20252026
BIG_PASS_N_SIMS = 1_000_000

# Which of the 1,000,000 simulations this section replays. Previously a
# standalone draw under its own dedicated seed, which meant the section had
# no real simulation number to quote. Replaced by a search over the big
# pass's own draws for this match: of the million, exactly 16 reproduce the
# published re-roll's per-shot outcomes EXACTLY (not merely its 1-4
# scoreline, which 7,703 do) -- so switching to one of them keeps every
# shot, the scoreline, and the section's hand-written commentary true while
# making the quoted sim number real. The 16 are 10917, 27967, 78441, 86684,
# 220032, 235660, 252470, 254894, 294772, 436482, 485151, 576401, 778161,
# 855000, 907004 and 976274; this is simply the lowest of them.
GAME_REROLL_SIM = 10917


def _match_rng(seed, match_index):
    return np.random.default_rng(np.random.SeedSequence([seed, match_index]))


def main():
    parser = argparse.ArgumentParser(description="Export one match's real shots + a single re-roll")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--home", required=True, help="Home team name, exactly as in the shots CSV")
    parser.add_argument("--away", required=True, help="Away team name, exactly as in the shots CSV")
    parser.add_argument("--sim", type=int, default=GAME_REROLL_SIM,
                        help="Which of the 1,000,000 simulations to replay")
    parser.add_argument("--seed", type=int, default=BIG_PASS_SEED)
    parser.add_argument("--n-sims", type=int, default=BIG_PASS_N_SIMS)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    shots = load_shots(args.shots)
    m = shots[(shots["h_team"] == args.home) & (shots["a_team"] == args.away)]
    if m.empty:
        raise SystemExit(f"no shots found for {args.home} vs {args.away} -- check team names/args.shots")
    match_id = int(m["match_id"].iloc[0])
    print(f"{args.home} vs {args.away} (match_id {match_id}): {len(m)} shots", file=sys.stderr)

    # Regenerate this match exactly as sim N of the big pass does. The draw
    # has to be requested at the full (n_sims, n_shots) shape, and home
    # before away off the same per-match generator, because draws_a's start
    # position in the stream depends on how many values draws_h consumed --
    # a smaller shape silently produces a different match (the bug
    # documented on export_treemap_data.py's build_campaign_for_sim).
    matches = build_match_index(shots)
    match_i = next(
        (i for i, mm in enumerate(matches) if mm["home_team"] == args.home and mm["away_team"] == args.away),
        None,
    )
    if match_i is None:
        raise SystemExit(f"no match found in the match index for {args.home} vs {args.away}")
    mx = matches[match_i]
    rng_i = _match_rng(args.seed, match_i)
    draws_h = rng_i.random((args.n_sims, len(mx["xg_h"]))) < mx["xg_h"]
    draws_a = rng_i.random((args.n_sims, len(mx["xg_a"]))) < mx["xg_a"]
    sim_h_row, sim_a_row = draws_h[args.sim], draws_a[args.sim]

    # build_match_index keeps each side's shots in plain CSV order, so map
    # each draw back onto its own CSV row before the minute sort below
    # reorders them for display. Keyed by the row's original index rather
    # than by position, since sorting by minute does not preserve each
    # side's internal order.
    side_rows = shots[shots["match_id"] == match_id]
    sim_by_row = {}
    for side, draws_row in (("h", sim_h_row), ("a", sim_a_row)):
        idx = side_rows[side_rows["h_a"] == side].index
        assert len(idx) == len(draws_row), "shot count mismatch between match index and CSV filter"
        for row_idx, scored in zip(idx, draws_row):
            sim_by_row[row_idx] = bool(scored)

    m = m.sort_values("minute", kind="stable")

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
        sim_goal = sim_by_row[i]
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
        "sim": int(args.sim),
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
    print(f"Sim:  {args.home} {sim_h}-{sim_a} {args.away}  (simulation #{args.sim:,})", file=sys.stderr)


if __name__ == "__main__":
    main()
