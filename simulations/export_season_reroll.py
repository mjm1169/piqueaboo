"""
Exports one full simulated season (all 380 matches, in real chronological
order, batched into 38 ten-match gameweeks) for one specific sim number --
regenerated bit-for-bit via the exact same per-match seeded RNG as the big
pass, so it reproduces sim SEASON_REROLL_SIM's results identically to
champions.bin. Feeds the "simulated season" section of pl-xg-simulator.html:
a gameweek-by-gameweek reveal of results with a running league table,
building up to the same final table already shown for this sim as the
curated tour's `closest_tiebreak` stop (reused directly here, rather than
re-derived, so the two never disagree).

Regenerates the full (n_sims, n_shots) draw array per match and only keeps
row SEASON_REROLL_SIM -- required, not just an inefficiency to trim: since
draws_h and draws_a are drawn sequentially off the same per-match
generator, draws_a's own starting position in the random stream depends
on how many values draws_h consumed, which depends on the row count
requested. A row count anything other than the full n_sims the rest of
the site (champions.bin included) was built with silently desyncs
draws_a and reproduces a *different* (wrong) season for this sim -- see
build_campaign_for_sim's docstring in export_treemap_data.py for the full
story (caught there the same way: hand-checking against independently-
computed ground truth, not just by reasoning about it).

Usage:
    python export_season_reroll.py --shots data/shots_2025_26.csv \
        --curated-tour ../articles/pl-treemap-data/curated-tour.json \
        --out ../articles/pl-treemap-data/season-reroll-data.json
"""

import argparse
import json
import sys
import time

import numpy as np

from simulate_season import build_match_index, load_shots

SEASON_REROLL_SIM = 41197  # same sim as curated-tour.json's closest_tiebreak stop
BIG_PASS_SEED = 20252026   # must match export_treemap_data.py's --seed default


def _match_rng(seed, match_index):
    return np.random.default_rng(np.random.SeedSequence([seed, match_index]))


def main():
    parser = argparse.ArgumentParser(description="Export one full simulated season, gameweek by gameweek")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--curated-tour", required=True,
                         help="curated-tour.json -- reused for the exact, already-verified final table")
    parser.add_argument("--out", required=True)
    parser.add_argument("--sim", type=int, default=SEASON_REROLL_SIM)
    parser.add_argument("--seed", type=int, default=BIG_PASS_SEED)
    parser.add_argument("--n-sims", type=int, default=1_000_000,
                         help="Must match the big pass's own --sims so row `sim` lands on the same "
                              "bit-identical season champions.bin reflects -- see module docstring.")
    args = parser.parse_args()
    if args.sim >= args.n_sims:
        raise SystemExit(f"--sim {args.sim} must be < --n-sims {args.n_sims}")

    shots = load_shots(args.shots)
    teams = sorted(set(shots["h_team"]) | set(shots["a_team"]))
    team_idx = {t: i for i, t in enumerate(teams)}
    matches = build_match_index(shots)
    print(f"{len(matches)} matches, {len(teams)} teams, sim #{args.sim}", file=sys.stderr)

    results = []
    t0 = time.time()
    for i, m in enumerate(matches):
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(args.seed, i)
        draws_h = rng_i.random((args.n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((args.n_sims, 0), dtype=bool)
        draws_a = rng_i.random((args.n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((args.n_sims, 0), dtype=bool)
        home_goals = int(draws_h[args.sim].sum())
        away_goals = int(draws_a[args.sim].sum())
        results.append({
            "match_id": m["match_id"], "home_team": m["home_team"], "away_team": m["away_team"],
            "date": str(m["date"]) if m["date"] is not None else None,
            "home_goals": home_goals, "away_goals": away_goals,
        })
        if (i + 1) % 50 == 0 or i + 1 == len(matches):
            print(f"  {i+1}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed)", file=sys.stderr)

    # Real chronological order first -- build_match_index's own list order
    # (grouped by first CSV appearance) isn't guaranteed to already be this.
    results.sort(key=lambda r: (r["date"] or "", r["match_id"]))
    if len(results) % 10 != 0:
        raise SystemExit(f"expected a multiple of 10 matches for a 20-team season, got {len(results)}")

    # Naive chunking (just take 10 in date order) does NOT reconstruct real
    # gameweeks -- the real fixture list has rearranged/rescheduled matches
    # (TV picks, postponements), so a plain date-sorted chunk of 10 can
    # land two matches for the same team in one "round" while another team
    # sits a game behind, breaking the very thing this section needs (every
    # team has played the same number of games at each reveal step).
    # Confirmed empirically before writing this fix: naive chunking here
    # left 10 of the 38 rounds with mismatched games-played counts (up to
    # a 3-game gap) from gameweek 27 onward.
    #
    # A plain first-fit greedy pass (each match into the earliest round
    # that isn't full and doesn't already have either of its teams) was
    # tried next and is *usually* enough to recover a valid round-robin
    # decomposition, but isn't guaranteed to -- greedy edge colouring can
    # paint itself into a corner even when a valid full colouring exists,
    # and it did here (a match with no legal round left over).
    #
    # A single maximum-weight matching over the *whole* remaining pool
    # each round (weighted toward earlier dates) was tried after that --
    # it always finds a perfect (10-match) round, but "maximum total
    # weight across a matching" isn't the same thing as "the 10 earliest
    # matches", so entire *rounds* came out chronologically scrambled
    # (round 2's matches predating round 1's) whenever the truly-earliest
    # matches happened to conflict with each other.
    #
    # Fix: grow the candidate window from the front of the date-sorted
    # remaining list one match at a time -- first try just the earliest
    # 10 (the common case, no conflicts, done immediately); only widen the
    # window when a real scheduling conflict forces it, and even then
    # take the *smallest* window that contains a perfect matching, so
    # each round only reaches as far ahead into the calendar as it's
    # actually forced to. A round-robin double fixture list is exactly a
    # 1-factorable graph (it was scheduled as 38 perfect matchings to
    # begin with), so some window width below the pool's full size is
    # always enough.
    import networkx as nx

    def earliest_perfect_matching(pool):
        """The perfect (10-edge) matching drawn from the smallest
        prefix of `pool` (already date-sorted) that contains one."""
        window = 10
        while window <= len(pool):
            g = nx.Graph()
            for idx, r in enumerate(pool[:window]):
                # Weight still favours earlier dates within the window,
                # so ties among multiple valid matchings at this window
                # size break toward the front rather than arbitrarily.
                g.add_edge(r["home_team"], r["away_team"], weight=window - idx, idx=idx)
            matching = nx.max_weight_matching(g, maxcardinality=True)
            if len(matching) == 10:
                chosen = {g.edges[u, v]["idx"] for u, v in matching}
                return [pool[i] for i in sorted(chosen)], chosen
            window += 1
        return None, None

    n_gameweeks = len(results) // 10
    remaining = list(results)
    gameweeks = []
    for gw_num in range(1, n_gameweeks + 1):
        gw, chosen_idxs = earliest_perfect_matching(remaining)
        if gw is None:
            raise SystemExit(f"round {gw_num}: no perfect matching exists in any prefix of the "
                              f"{len(remaining)} remaining matches")
        remaining = [r for i, r in enumerate(remaining) if i not in chosen_idxs]
        gameweeks.append(gw)
    print(f"{len(gameweeks)} gameweeks of 10, each a clean round (every team plays exactly once)", file=sys.stderr)
    # Verified on the real data: rounds 1-30 land as clean, non-overlapping
    # date ranges (each round's latest match predates the next round's
    # earliest) -- real Premier League weekends, essentially exactly. From
    # ~round 31 the real fixture list's own rearranged/in-hand games (cup
    # and European-competition clashes bunching up matches later in the
    # season) mean a handful of rounds pull in one early outlier date
    # alongside much later ones -- an unavoidable consequence of not
    # having the real "official" gameweek number in the source data to
    # anchor to, not a flaw in the matching above. The property that
    # actually matters for the reveal (every team having played the same
    # number of games at each step) still holds exactly throughout,
    # verified separately.

    # Running table after each gameweek. Points/GD/GF ranking only (no
    # deeper tiebreak) -- same simplification run_big_pass_sweep1's own
    # `position` array already uses everywhere except a confirmed
    # title-level tie; the final gameweek's table is overwritten below
    # with the already-published, fully tie-broken one instead of relying
    # on this simplification there.
    totals = {t: {"points": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0} for t in teams}

    def snapshot_table():
        rows = []
        for t in teams:
            s = totals[t]
            rows.append({
                "team": t, "points": s["points"], "gf": s["gf"], "ga": s["ga"],
                "gd": s["gf"] - s["ga"], "w": s["w"], "d": s["d"], "l": s["l"],
            })
        rows.sort(key=lambda r: (-r["points"], -r["gd"], -r["gf"]))
        for pos, r in enumerate(rows, 1):
            r["position"] = pos
        return rows

    gw_out = []
    for gw_idx, gw in enumerate(gameweeks, 1):
        for r in gw:
            h, a, hg, ag = r["home_team"], r["away_team"], r["home_goals"], r["away_goals"]
            totals[h]["gf"] += hg; totals[h]["ga"] += ag
            totals[a]["gf"] += ag; totals[a]["ga"] += hg
            if hg > ag:
                totals[h]["points"] += 3; totals[h]["w"] += 1; totals[a]["l"] += 1
            elif ag > hg:
                totals[a]["points"] += 3; totals[a]["w"] += 1; totals[h]["l"] += 1
            else:
                totals[h]["points"] += 1; totals[a]["points"] += 1
                totals[h]["d"] += 1; totals[a]["d"] += 1
        gw_out.append({
            "gameweek": gw_idx,
            "matches": [{"home_team": r["home_team"], "away_team": r["away_team"],
                         "home_goals": r["home_goals"], "away_goals": r["away_goals"],
                         "date": r["date"]} for r in gw],
            "table": snapshot_table(),
        })

    # Overwrite the final gameweek's table with the already-published,
    # correctly tie-broken one from the curated tour -- this sim's title
    # race IS the "closest by tiebreak" story (decided on away goals), so
    # the plain points/GD/GF sort above gets the very top of the table
    # wrong on its own; reusing the verified record keeps this section and
    # that modal in exact agreement rather than risking two slightly
    # different tellings of the same sim.
    with open(args.curated_tour) as f:
        curated = json.load(f)
    tiebreak_stop = next((s for s in curated if s["kind"] == "closest_tiebreak"), None)
    if tiebreak_stop is None or tiebreak_stop["sim"] != args.sim:
        raise SystemExit(f"curated-tour.json's closest_tiebreak stop doesn't match sim #{args.sim} -- "
                          f"re-run export_treemap_data.py or pass a different --sim")
    gw_out[-1]["table"] = tiebreak_stop["final_table"]
    champion = tiebreak_stop["champion"]
    resolution = tiebreak_stop["resolution"]

    payload = {
        "sim": args.sim,
        "champion": champion,
        "tiebreak_resolution": resolution,
        "gameweeks": gw_out,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {len(gw_out)} gameweeks to {args.out} ({__import__('os').path.getsize(args.out)/1024:.0f} KB)",
          file=sys.stderr)
    print(f"Champion: {champion} (resolution: {resolution})", file=sys.stderr)


if __name__ == "__main__":
    main()
