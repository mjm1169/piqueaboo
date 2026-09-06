"""
Exports one full simulated season (all 380 matches, in real chronological
order, batched into 38 ten-match gameweeks) for the "simulated season"
section of pl-xg-simulator.html: a gameweek-by-gameweek reveal of results
with a running league table.

Standalone, illustrative re-roll of the *whole* season -- same convention
as export_game_reroll.py's own single-match re-roll, and NOT tied to the
1,000,000-sim big pass / champions.bin the rest of the site's treemap
draws from. Uses the same per-match seeded RNG scheme as the big pass
(`_match_rng`, home/away goal arrays drawn separately per match) so a
match's goals are drawn the same *way* everything else on this site is,
but under its own dedicated seed, one throwaway sim row (0), regenerated
fresh each run rather than looked up by number in champions.bin.

The seed is fixed, not arbitrary: the season section immediately follows
the single-match re-roll of the year's opening fixture (Liverpool vs
Bournemouth), and the two need to agree on that one match's own gameweek-1
result or the page would show two different scorelines for the same
match one scroll apart. SEASON_REROLL_SEED was found by searching seeds
for one whose gameweek-1 Liverpool/Bournemouth score exactly matches
game-reroll-data.json's own sim_final_score (Liverpool 1-4 Bournemouth) --
same "search a seed range for a specific target" convention as
GAME_REROLL_SEED in export_game_reroll.py, just matched against a
concrete scoreline instead of "any divergent outcome". Of the candidates
that clear that bar, this one was picked because it also happens to
produce a genuinely different, unexpected champion (Chelsea, real 2025/26
finish: 10th) with a clean, tie-free title race -- in keeping with this
whole article's "a very different result could have happened" theme,
rather than reproducing the real champion or an otherwise unremarkable
table.

Regenerates the full (n_sims, n_shots) draw array per match and only keeps
row 0 -- required, not just an inefficiency to trim: since draws_h and
draws_a are drawn sequentially off the same per-match generator, draws_a's
own starting position in the random stream depends on how many values
draws_h consumed, which depends on the row count requested. See
build_campaign_for_sim's docstring in export_treemap_data.py for the full
story of how a truncated shape silently desyncs draws_a and reproduces a
*different* (wrong) season -- caught there the same way: hand-checking
against independently-computed ground truth, not just by reasoning about
it. n_sims=1 is fine precisely because nothing upstream of this script
ever draws a different, larger shape for the same seed/match that this
would need to stay in sync with (unlike the big pass's shared
champions.bin, this seed belongs to nothing else).

Champion is picked via the real Premier League tie-break chain
(build_h2h_fixture_index/resolve_tied_group, same code path the big pass's
own sweep2 uses for a genuine title-level tie) rather than the plain
points/GD/GF sort used for every other gameweek's running table -- belt
and braces, since unlike the big pass this season has no other
already-published table to fall back on if the plain sort ever did land
on a real tie. On the current data/seed it doesn't (Chelsea wins clean),
but the chain runs regardless so this stays correct if the source data or
seed ever changes.

Usage:
    python export_season_reroll.py --shots data/shots_2025_26.csv \
        --out ../articles/pl-treemap-data/season-reroll-data.json
"""

import argparse
import json
import sys
import time

import numpy as np

from simulate_season import build_h2h_fixture_index, build_match_index, load_shots, resolve_tied_group

# See the module docstring for how and why this specific seed was chosen.
SEASON_REROLL_SEED = 596


def _match_rng(seed, match_index):
    return np.random.default_rng(np.random.SeedSequence([seed, match_index]))


def main():
    parser = argparse.ArgumentParser(description="Export one standalone full simulated season, gameweek by gameweek")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--seed", type=int, default=SEASON_REROLL_SEED)
    args = parser.parse_args()

    shots = load_shots(args.shots)
    teams = sorted(set(shots["h_team"]) | set(shots["a_team"]))
    team_idx = {t: i for i, t in enumerate(teams)}
    matches = build_match_index(shots)
    fixture_index = build_h2h_fixture_index(matches, team_idx)
    print(f"{len(matches)} matches, {len(teams)} teams, seed {args.seed}", file=sys.stderr)

    results = []
    t0 = time.time()
    for i, m in enumerate(matches):
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(args.seed, i)
        draws_h = rng_i.random((1, len(xg_h))) < xg_h if len(xg_h) else np.zeros((1, 0), dtype=bool)
        draws_a = rng_i.random((1, len(xg_a))) < xg_a if len(xg_a) else np.zeros((1, 0), dtype=bool)
        home_goals = int(draws_h[0].sum())
        away_goals = int(draws_a[0].sum())
        results.append({
            "match_id": m["match_id"], "home_team": m["home_team"], "away_team": m["away_team"],
            "date": str(m["date"]) if m["date"] is not None else None,
            "home_goals": home_goals, "away_goals": away_goals,
        })
        if (i + 1) % 50 == 0 or i + 1 == len(matches):
            print(f"  {i+1}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed)", file=sys.stderr)

    lb = next((r for r in results if r["home_team"] == "Liverpool" and r["away_team"] == "Bournemouth"), None)
    if lb is None or (lb["home_goals"], lb["away_goals"]) != (1, 4):
        raise SystemExit(f"seed {args.seed} no longer gives Liverpool 1-4 Bournemouth in gameweek 1 "
                          f"(got {lb}) -- shots data must have changed since this seed was picked; "
                          f"search for a new one (see module docstring)")

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
    if gameweeks[0][0]["home_team"] != "Liverpool" or gameweeks[0][0]["away_team"] != "Bournemouth":
        raise SystemExit("Liverpool vs Bournemouth didn't land as gameweek 1's own first-listed match -- "
                          "matching/order assumption broken, investigate before shipping")

    # Running table after each gameweek. Points/GD/GF ranking only (no
    # deeper tiebreak) for the interim, gameweek-by-gameweek snapshots --
    # nobody's tracking a mid-season tiebreak scenario game to game, and
    # the final gameweek's table (below) gets the real chain regardless.
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

    # Real tie-break chain for the final table only -- see module
    # docstring. get_result looks up a match by its position in `matches`
    # (the same indexing fixture_index/_match_rng use), not `results`
    # (chronologically re-sorted above), so build a fresh lookup keyed the
    # same way build_h2h_fixture_index itself indexes matches.
    result_by_match_id = {r["match_id"]: r for r in results}
    match_result_by_index = {
        i: (result_by_match_id[m["match_id"]]["home_goals"], result_by_match_id[m["match_id"]]["away_goals"])
        for i, m in enumerate(matches)
    }

    def get_result(match_idx):
        return match_result_by_index[match_idx]

    final_table = gw_out[-1]["table"]
    top_points, top_gd, top_gf = final_table[0]["points"], final_table[0]["gd"], final_table[0]["gf"]
    tied = [r for r in final_table if (r["points"], r["gd"], r["gf"]) == (top_points, top_gd, top_gf)]
    resolution = "none"
    if len(tied) > 1:
        tied_idxs = [team_idx[r["team"]] for r in tied]
        order, resolution = resolve_tied_group(tied_idxs, fixture_index, get_result,
                                                rng=np.random.default_rng(args.seed))
        champion_team = teams[order[0]]
        # Re-rank just the tied group by the tie-break order found; every
        # other team keeps its plain-sort position among itself.
        tied_rank = {teams[t]: rank for rank, t in enumerate(order)}
        final_table.sort(key=lambda r: tied_rank.get(r["team"], len(order)))
        for pos, r in enumerate(final_table, 1):
            r["position"] = pos
    else:
        champion_team = final_table[0]["team"]
    gw_out[-1]["table"] = final_table

    payload = {
        "seed": args.seed,
        "champion": champion_team,
        "tiebreak_resolution": resolution,
        "gameweeks": gw_out,
    }
    with open(args.out, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    print(f"Wrote {len(gw_out)} gameweeks to {args.out} ({__import__('os').path.getsize(args.out)/1024:.0f} KB)",
          file=sys.stderr)
    print(f"Champion: {champion_team} (resolution: {resolution})", file=sys.stderr)


if __name__ == "__main__":
    main()
