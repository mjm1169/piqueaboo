"""
Build the data behind the "1,000,000 simulated seasons" title-race treemap.

Three passes, at very different scales, feed the outputs:

  1. The big pass's first sweep (n_sims = --sims, meant to be run at
     ~1,000,000) is the spatial backbone of the treemap -- every one of its
     sims is a real, addressable cell -- and it applies a three-tier save
     policy per sim, cheapest tier first:
       - By default: just WHO WON. Dumped as a compact binary file, one
         byte per simulation (the champion's team index) -- this alone is
         what drives the treemap's layout (title count per team) and the
         fill colour of every cell.
       - If the champion's REAL-life finishing position was outside the
         top half of the table ("unexpected winner"): the sim's full final
         table is additionally kept (flagged-champions.json).
       - If any single match in that sim finished with a very high combined
         score, or one player scored a large individual haul: that match's
         full detail -- including a full ordered scorecard, not just the
         final score -- is additionally kept (flagged-games.json). A
         6+-goal individual haul is capped to the single best-qualifying
         sim per real fixture (these turn out to cluster heavily on a
         handful of shot-heavy real matches, so keeping every raw hit
         would just be thousands of near-duplicates of the same few
         fixtures).
     All of this happens in one streaming sweep over the matches
     (vectorised across all n_sims per match) -- the per-sim points/gf/ga
     totals needed for final standings are already carried through to the
     end regardless, so the "unexpected winner" tier costs nothing extra;
     the per-match threshold checks are cheap vectorised comparisons made
     while that match's goal arrays are already in scope, discarded once
     the sweep moves to the next match.

  2. The big pass's SECOND sweep exists for one reason: points/GD/GF alone
     can't crown a champion when two teams tie on all three -- the real
     tie-break chain (head-to-head points, then head-to-head away goals,
     then a coin flip standing in for a play-off) needs the actual results
     of the specific matches between the tied teams, which sweep 1 never
     retains (that's what keeps 1,000,000 sims affordable in the first
     place). This is rare enough at the *title* level (~30 sims per
     million, calibrated) that a second full sweep to regenerate exactly
     what's needed is cheap relative to sweep 1. It's made possible by
     seeding each match's random draws independently --
     np.random.default_rng(SeedSequence([seed, match_index])) instead of
     one shared stream consumed match-by-match -- so any single match's
     draws-for-every-sim can be regenerated bit-for-bit identically on
     demand, without replaying the matches before it. The same sweep also
     builds the full 38-game campaign log (opponent, H/A, sim score, xG
     score) for every unexpected-winner flagged champion, since it's
     already regenerating match results anyway and the marginal cost of
     also capturing a flagged champion's own fixtures is negligible.

  3. A small, separate, decoupled pass (n_sims = --story-sims, a few
     thousand) that additionally keeps every match's scoreline for every
     one of its sims (affordable at this scale, not at 1,000,000).
     "Interesting" simulated seasons are picked out of *this* batch --
     closest title races, biggest upset champions, etc -- each with a full
     final table and its own notable games, feeding the roster's per-team
     story cards. This is a different, pre-existing feature from the
     flagged-sim data above: every simulation is an independent,
     identically-distributed draw from the same model, so a "closest title
     race" example pulled from this small batch is just as genuine an
     illustration as one pulled from the big one would be -- there's no
     meaningful sense in which one specific one-in-a-million column is
     "more real" than a same-shaped example from a separate batch. Unlike
     the flagged-sim data, though, these examples aren't tied to any
     specific cell in the treemap grid. It also gets the real head-to-head
     tie-break chain (for every position, not just the title) applied to
     its own final tables, cheaply, since it already retains full match
     detail for every one of its (much smaller number of) sims.

Usage:
    python export_treemap_data.py --shots data/shots_2025_26.csv \
        --teams-meta ../assets/logos/clubs/teams_2025_26.json \
        --out-dir ../articles/pl-treemap-data \
        --sims 1000000 --story-sims 20000
"""

import argparse
import json
import os
import sys
import time
from collections import defaultdict

import numpy as np

from simulate_season import (
    build_h2h_fixture_index,
    build_match_index,
    build_real_table,
    load_shots,
    resolve_tied_group,
)


# Distinct from any real match index (0..~379), used to seed the coin-flip
# stage of tie resolution separately from the per-match draw streams.
COIN_FLIP_SEED_OFFSET = 10_000_000


def _match_rng(seed, match_index):
    """An independent, reproducible RNG stream for one match -- the whole
    point being that any single match's draws-for-all-sims can be
    regenerated bit-for-bit identically later (sweep 2) without replaying
    every match before it, unlike one shared stream consumed in sequence."""
    return np.random.default_rng(np.random.SeedSequence([seed, match_index]))


def build_team_fixture_index(matches, teams):
    """team name -> list of match indices (both home and away legs) --
    that team's 38 real fixtures, in real fixture-list order. Static,
    independent of any simulation."""
    idx = {t: [] for t in teams}
    for i, m in enumerate(matches):
        idx[m["home_team"]].append(i)
        idx[m["away_team"]].append(i)
    return idx


def static_match_xg(matches):
    """[(xg_home_total, xg_away_total), ...] per match -- the sum of that
    match's real shots' xG per side. Independent of simulation: every sim
    replays the same shots, only whether each one goes in changes."""
    return [(float(m["xg_h"].sum()), float(m["xg_a"].sum())) for m in matches]


def extract_scorecard(sim_idx, draws, players, minutes, is_pen, team):
    """Ordered-by-minute list of {player, minute, penalty, team} for every
    shot that actually scored in this one sim's column of one match."""
    entries = []
    for shot_idx in np.flatnonzero(draws[sim_idx]).tolist():
        entries.append({
            "player": str(players[shot_idx]),
            "minute": int(minutes[shot_idx]) if minutes is not None else None,
            "penalty": bool(is_pen[shot_idx]) if is_pen is not None else False,
            "team": team,
        })
    entries.sort(key=lambda e: (e["minute"] is None, e["minute"]))
    return entries


def run_big_pass_sweep1(matches, teams, n_sims, real_pos, seed=None,
                         high_score_threshold=15, haul_threshold=6):
    """
    The big (~1,000,000-sim) pass's first sweep. Vectorised across all
    n_sims, one match at a time -- keeps only what the three-tier save
    policy actually needs:

      - points/gf/ga per sim, all the way through (already required to work
        out final standings/champion -- no extra cost for the "unexpected
        winner" tier).
      - per match, while its home/away goal arrays for all n_sims are still
        in scope: which sims cleared the high-scoring bar (kept as-is, no
        dedup -- rare enough already at this threshold) with a full scorer
        list, and the single best-qualifying sim for a 6+-goal individual
        haul (capped to one per real fixture -- see module docstring).

    Deliberately doesn't retain any full (n_matches, n_sims) match array --
    that's what keeps 1,000,000 sims affordable. Once a match's iteration
    is done, only the handful of qualifying records for it survive.

    Champion/position here is provisional wherever a sim is tied at the
    title (points/GD/GF all equal for 2+ teams) -- those sims are flagged
    as pending for sweep 2 to resolve properly via head-to-head. Everywhere
    else (the ~99.997% of sims with no title-level tie) this is already
    the final answer.
    """
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}

    points = np.zeros((n_sims, n_teams), dtype=np.int32)
    gf = np.zeros((n_sims, n_teams), dtype=np.int32)
    ga = np.zeros((n_sims, n_teams), dtype=np.int32)

    flagged_games = []

    t0 = time.time()
    for i, m in enumerate(matches, 1):
        mi = i - 1
        h_idx, a_idx = team_idx[m["home_team"]], team_idx[m["away_team"]]
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, mi)

        draws_h = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)

        home_goals = draws_h.sum(axis=1)
        away_goals = draws_a.sum(axis=1)

        points[:, h_idx] += np.where(home_goals > away_goals, 3, np.where(home_goals == away_goals, 1, 0))
        points[:, a_idx] += np.where(away_goals > home_goals, 3, np.where(home_goals == away_goals, 1, 0))
        gf[:, h_idx] += home_goals
        ga[:, h_idx] += away_goals
        gf[:, a_idx] += away_goals
        ga[:, a_idx] += home_goals

        # --- high-scoring games: keep every qualifying sim for this match ---
        total = home_goals + away_goals
        match_flags = {}  # sim -> record, so a haul below can merge into an
                           # existing high-scoring record for the same sim
        for s in np.flatnonzero(total >= high_score_threshold).tolist():
            match_flags[s] = {
                "sim": s, "match_id": m["match_id"],
                "home_team": m["home_team"], "away_team": m["away_team"],
                "home_goals": int(home_goals[s]), "away_goals": int(away_goals[s]),
                "date": m["date"], "triggers": ["high_scoring"],
            }

        # --- 6+-goal individual haul: single best-qualifying sim for this
        # real fixture only, across every player on either side ---
        haul_best = None
        for draws, players, team, opponent in (
            (draws_h, m["players_h"], m["home_team"], m["away_team"]),
            (draws_a, m["players_a"], m["away_team"], m["home_team"]),
        ):
            if draws.shape[1] == 0:
                continue
            for player in np.unique(players):
                cols = players == player
                player_goals = draws[:, cols].sum(axis=1)
                best_s = int(np.argmax(player_goals))
                best_val = int(player_goals[best_s])
                if best_val >= haul_threshold and (haul_best is None or best_val > haul_best["goals"]):
                    haul_best = {"sim": best_s, "player": str(player), "team": team,
                                 "opponent": opponent, "goals": best_val}

        if haul_best is not None:
            s = haul_best["sim"]
            haul_info = {"player": haul_best["player"], "team": haul_best["team"], "goals": haul_best["goals"]}
            if s in match_flags:
                match_flags[s]["triggers"].append("six_plus_haul")
                match_flags[s]["haul"] = haul_info
            else:
                match_flags[s] = {
                    "sim": s, "match_id": m["match_id"],
                    "home_team": m["home_team"], "away_team": m["away_team"],
                    "home_goals": int(home_goals[s]), "away_goals": int(away_goals[s]),
                    "date": m["date"], "triggers": ["six_plus_haul"], "haul": haul_info,
                }

        # Full scorecard for every sim that ended up flagged on this match,
        # for either reason -- built once the flags for this match are
        # settled, while draws/players/minutes are still in scope. Merged
        # across both sides and re-sorted so the list reads as a genuine
        # match timeline, not "all home goals, then all away goals".
        for s, record in match_flags.items():
            scorers = (
                extract_scorecard(s, draws_h, m["players_h"], m["minutes_h"], m["is_pen_h"], m["home_team"])
                + extract_scorecard(s, draws_a, m["players_a"], m["minutes_a"], m["is_pen_a"], m["away_team"])
            )
            scorers.sort(key=lambda e: (e["minute"] is None, e["minute"]))
            record["scorers"] = scorers

        flagged_games.extend(match_flags.values())

        if i % 50 == 0 or i == len(matches):
            print(f"  [big pass, sweep 1] {i}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed, "
                  f"{len(flagged_games)} flagged games so far)", file=sys.stderr)

    gd = gf - ga
    rank_key = points.astype(np.int64) * 10_000_000 + (gd.astype(np.int64) + 500) * 10_000 + gf.astype(np.int64)
    order = np.argsort(-rank_key, axis=1)
    position = np.argsort(order, axis=1) + 1
    champion_idx = order[:, 0].copy()  # provisional -- patched for pending sims after sweep 2

    # --- title-level ties: any sim where 2+ teams share the very top
    # rank_key value need sweep 2's head-to-head resolution before their
    # champion is final ---
    sorted_key = np.take_along_axis(rank_key, order, axis=1)
    title_tie_mask = sorted_key[:, 0] == sorted_key[:, 1]
    pending_sims = []
    for s in np.flatnonzero(title_tie_mask).tolist():
        top_key = sorted_key[s, 0]
        tied_idxs = [int(order[s, k]) for k in range(n_teams) if rank_key[s, order[s, k]] == top_key]
        pending_sims.append({"sim": s, "tied_idxs": tied_idxs})
    if pending_sims:
        print(f"  [big pass, sweep 1] {len(pending_sims)} sim(s) tied at the title level, "
              f"pending sweep 2", file=sys.stderr)

    # --- unexpected winners: every sim (not pending) whose champion's
    # real-life position was outside the top half of the table gets its
    # full final table kept ---
    pending_sim_set = {p["sim"] for p in pending_sims}
    champ_real_pos = np.array([real_pos[teams[i]] for i in champion_idx])
    upset_mask = (champ_real_pos > (n_teams // 2))
    flagged_champions = {}
    for s in np.flatnonzero(upset_mask).tolist():
        if s in pending_sim_set:
            continue  # resolved (and, if still an upset, added) after sweep 2
        flagged_champions[s] = {
            "sim": s,
            "champion": teams[champion_idx[s]],
            "champion_real_position": int(champ_real_pos[s]),
            "final_table": build_final_table(points, gf, ga, position, s, teams),
        }

    return {
        "points": points, "gf": gf, "ga": ga, "position": position,
        "champion_idx": champion_idx, "rank_key": rank_key,
        "flagged_champions": flagged_champions,
        "flagged_games": flagged_games,
        "pending_sims": pending_sims,
    }


def build_final_table(points, gf, ga, position, sim_idx, teams):
    """Full final table for one sim, read straight out of the big pass's
    points/gf/ga/position arrays (kept for all n_sims regardless -- see
    run_big_pass_sweep1)."""
    rows = []
    for i, t in enumerate(teams):
        rows.append({
            "team": t,
            "position": int(position[sim_idx, i]),
            "points": int(points[sim_idx, i]),
            "gf": int(gf[sim_idx, i]),
            "ga": int(ga[sim_idx, i]),
            "gd": int(gf[sim_idx, i] - ga[sim_idx, i]),
        })
    rows.sort(key=lambda r: r["position"])
    return rows


def run_big_pass_sweep2(matches, teams, n_sims, seed, team_idx, fixture_index,
                         pending_sims, flagged_champions, static_xg):
    """
    The big pass's second sweep. Regenerates every match's draws via the
    same per-match independent seeding as sweep 1 (bit-identical results),
    gathering exactly two things sweep 1 couldn't afford to retain:

      - the specific head-to-head results needed to resolve each pending
        title tie (which fixtures matter is known up front from
        pending_sims -- only those matches' relevant sim columns get used).
      - a full 38-game campaign log for every already-confirmed
        unexpected-winner flagged champion, and -- since a pending sim's
        eventual champion isn't known until after this sweep -- a
        *candidate* campaign for every team still tied in a pending sim,
        with the wrong candidate(s) simply discarded once resolved.
    """
    sims_by_team = defaultdict(list)
    for s, rec in flagged_champions.items():
        sims_by_team[rec["champion"]].append(s)

    pending_candidates = {p["sim"]: {teams[t]: [] for t in p["tied_idxs"]} for p in pending_sims}
    pending_h2h_results = {p["sim"]: {} for p in pending_sims}

    match_to_pending = defaultdict(list)  # match_index -> [pending sim, ...]
    for p in pending_sims:
        tied = p["tied_idxs"]
        needed = set()
        for i in range(len(tied)):
            for j in range(i + 1, len(tied)):
                for match_idx, _h, _a in fixture_index.get(frozenset((tied[i], tied[j])), []):
                    needed.add(match_idx)
        for match_idx in needed:
            match_to_pending[match_idx].append(p["sim"])

    campaign_entries = defaultdict(list)

    t0 = time.time()
    for i, m in enumerate(matches, 1):
        mi = i - 1
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, mi)

        draws_h = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)
        home_goals = draws_h.sum(axis=1)
        away_goals = draws_a.sum(axis=1)

        for sim in match_to_pending.get(mi, []):
            pending_h2h_results[sim][mi] = (int(home_goals[sim]), int(away_goals[sim]))

        xg_home, xg_away = static_xg[mi]
        for team, opponent, is_home, xg_for, xg_against in (
            (m["home_team"], m["away_team"], True, xg_home, xg_away),
            (m["away_team"], m["home_team"], False, xg_away, xg_home),
        ):
            entry_template = lambda sim: {  # noqa: E731 -- tiny, scoped, clearer inline
                "opponent": opponent, "home": is_home, "date": m["date"],
                "sim_goals_for": int(home_goals[sim]) if is_home else int(away_goals[sim]),
                "sim_goals_against": int(away_goals[sim]) if is_home else int(home_goals[sim]),
                "xg_for": round(xg_for, 2), "xg_against": round(xg_against, 2),
            }
            for sim in sims_by_team.get(team, []):
                campaign_entries[sim].append(entry_template(sim))
            for sim, candidates in pending_candidates.items():
                if team in candidates:
                    candidates[team].append(entry_template(sim))

        if i % 50 == 0 or i == len(matches):
            print(f"  [big pass, sweep 2] {i}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed)",
                  file=sys.stderr)

    return {
        "campaign_entries": campaign_entries,
        "pending_h2h_results": pending_h2h_results,
        "pending_candidates": pending_candidates,
    }


def finalize_big_pass(sweep1, sweep2, teams, real_pos, fixture_index, seed):
    """
    Attaches campaign logs to already-confirmed flagged champions, then
    resolves every pending title tie via the real head-to-head chain
    (resolve_tied_group), patching champion_idx/position for those sims,
    adding them to flagged_champions if the resolved champion also turns
    out to be an unexpected winner, and building flagged-title-ties.json's
    records regardless of upset status (a title decided on head-to-head is
    noteworthy on its own, whoever it favours).
    """
    points, gf, ga, position = sweep1["points"], sweep1["gf"], sweep1["ga"], sweep1["position"]
    champion_idx = sweep1["champion_idx"]
    n_teams = len(teams)

    flagged_champions = sweep1["flagged_champions"]
    for sim, rec in flagged_champions.items():
        rec["campaign"] = sweep2["campaign_entries"].get(sim, [])

    coin_rng = np.random.default_rng(np.random.SeedSequence([seed, COIN_FLIP_SEED_OFFSET]))
    flagged_title_ties = []
    for p in sweep1["pending_sims"]:
        sim, tied_idxs = p["sim"], p["tied_idxs"]
        h2h_results = sweep2["pending_h2h_results"][sim]
        order, criterion = resolve_tied_group(tied_idxs, fixture_index, lambda mi: h2h_results[mi], rng=coin_rng)

        for rank, team_i in enumerate(order):
            position[sim, team_i] = rank + 1
        champion_idx[sim] = order[0]
        champion_name = teams[order[0]]
        champ_real_position = real_pos[champion_name]

        campaign = sweep2["pending_candidates"][sim][champion_name]
        final_table = build_final_table(points, gf, ga, position, sim, teams)

        if champ_real_position > (n_teams // 2):
            flagged_champions[sim] = {
                "sim": sim, "champion": champion_name,
                "champion_real_position": int(champ_real_position),
                "final_table": final_table, "campaign": campaign,
            }

        h2h_matches = []
        for i in range(len(tied_idxs)):
            for j in range(i + 1, len(tied_idxs)):
                for match_idx, home_i, away_i in fixture_index.get(frozenset((tied_idxs[i], tied_idxs[j])), []):
                    hg, ag = h2h_results[match_idx]
                    h2h_matches.append({"home_team": teams[home_i], "away_team": teams[away_i],
                                         "home_goals": hg, "away_goals": ag})

        flagged_title_ties.append({
            "sim": sim, "champion": champion_name,
            "champion_real_position": int(champ_real_position),
            "tied_teams": [teams[t] for t in tied_idxs],
            "resolution": criterion,
            "h2h_matches": h2h_matches,
            "final_table": final_table,
            "campaign": campaign,
        })

    return list(flagged_champions.values()), flagged_title_ties


def run_simulation_with_matches(matches, teams, n_sims, seed=None,
                                 thriller_threshold=7, hattrick_threshold=3):
    """
    Same Monte Carlo loop as run_simulation(), but additionally retains
    every match's home/away goals for every simulation in the batch (not
    just the single best-sim-per-match that run_simulation keeps for its
    "showcase" extremes) -- only affordable at the smaller "story" batch
    size, which is the whole reason this is a separate function rather
    than a flag on run_simulation itself.
    """
    rng = np.random.default_rng(seed)
    n_teams = len(teams)
    n_matches = len(matches)
    team_idx = {t: i for i, t in enumerate(teams)}

    points = np.zeros((n_sims, n_teams), dtype=np.int32)
    gf = np.zeros((n_sims, n_teams), dtype=np.int32)
    ga = np.zeros((n_sims, n_teams), dtype=np.int32)
    thriller_count = np.zeros(n_sims, dtype=np.int32)
    hattrick_count = np.zeros(n_sims, dtype=np.int32)

    # goals[i, s] = goals scored by the home/away side of match i, in sim s.
    # int16 (not int8): safe headroom over any plausible single-match tally.
    match_home_goals = np.zeros((n_matches, n_sims), dtype=np.int16)
    match_away_goals = np.zeros((n_matches, n_sims), dtype=np.int16)

    t0 = time.time()
    for i, m in enumerate(matches):
        h_idx, a_idx = team_idx[m["home_team"]], team_idx[m["away_team"]]
        xg_h, xg_a = m["xg_h"], m["xg_a"]

        draws_h = rng.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)

        home_goals = draws_h.sum(axis=1)
        away_goals = draws_a.sum(axis=1)
        match_home_goals[i, :] = home_goals
        match_away_goals[i, :] = away_goals

        points[:, h_idx] += np.where(home_goals > away_goals, 3, np.where(home_goals == away_goals, 1, 0))
        points[:, a_idx] += np.where(away_goals > home_goals, 3, np.where(home_goals == away_goals, 1, 0))
        gf[:, h_idx] += home_goals
        ga[:, h_idx] += away_goals
        gf[:, a_idx] += away_goals
        ga[:, a_idx] += home_goals

        total = home_goals + away_goals
        thriller_count += (total >= thriller_threshold)

        for draws, players in ((draws_h, m["players_h"]), (draws_a, m["players_a"])):
            if draws.shape[1] == 0:
                continue
            for player in set(players):
                cols = players == player
                player_goals = draws[:, cols].sum(axis=1)
                hattrick_count += (player_goals >= hattrick_threshold)

        if (i + 1) % 50 == 0 or i + 1 == n_matches:
            print(f"  [story batch] {i+1}/{n_matches} matches ({time.time()-t0:.1f}s elapsed)", file=sys.stderr)

    gd = gf - ga
    rank_key = points.astype(np.int64) * 10_000_000 + (gd.astype(np.int64) + 500) * 10_000 + gf.astype(np.int64)
    order = np.argsort(-rank_key, axis=1)
    position = np.argsort(order, axis=1) + 1
    champion_idx = order[:, 0]

    return {
        "teams": teams, "points": points, "gf": gf, "ga": ga, "gd": gd,
        "position": position, "champion_idx": champion_idx,
        "thriller_count": thriller_count, "hattrick_count": hattrick_count,
        "match_home_goals": match_home_goals, "match_away_goals": match_away_goals,
    }


def apply_full_tiebreaks_to_batch(sim, fixture_index, seed):
    """
    Patches sim['position']/sim['champion_idx'] in place, resolving every
    tie -- any position, not just the title -- via the real head-to-head
    chain. Affordable here (unlike the 1,000,000-sim big pass) because
    match_home_goals/match_away_goals are already retained for every sim
    in this batch, so no second sweep is needed: resolve_tied_group() can
    just read straight out of them.
    """
    n_sims, n_teams = sim["points"].shape
    rank_key = sim["points"].astype(np.int64) * 10_000_000 + \
        (sim["gd"].astype(np.int64) + 500) * 10_000 + sim["gf"].astype(np.int64)
    order = np.argsort(-rank_key, axis=1)
    sorted_key = np.take_along_axis(rank_key, order, axis=1)
    has_tie = (sorted_key[:, :-1] == sorted_key[:, 1:]).any(axis=1)

    mh, ma = sim["match_home_goals"], sim["match_away_goals"]
    position = sim["position"]
    champion_idx = sim["champion_idx"] = sim["champion_idx"].copy()
    coin_rng = np.random.default_rng(np.random.SeedSequence([seed, COIN_FLIP_SEED_OFFSET]))

    for s in np.flatnonzero(has_tie).tolist():
        get_result = lambda mi, _s=s: (int(mh[mi, _s]), int(ma[mi, _s]))  # noqa: E731
        row_order, row_keys = order[s].tolist(), sorted_key[s].tolist()
        final = []
        i = 0
        while i < n_teams:
            j = i
            while j + 1 < n_teams and row_keys[j + 1] == row_keys[i]:
                j += 1
            group = row_order[i:j + 1]
            if len(group) > 1:
                resolved, _criterion = resolve_tied_group(group, fixture_index, get_result, rng=coin_rng)
                final.extend(resolved)
            else:
                final.extend(group)
            i = j + 1
        for rank, team_i in enumerate(final):
            position[s, team_i] = rank + 1
        champion_idx[s] = final[0]


def team_final_table(sim, sim_idx, teams):
    rows = []
    for i, t in enumerate(teams):
        rows.append({
            "team": t,
            "position": int(sim["position"][sim_idx, i]),
            "points": int(sim["points"][sim_idx, i]),
            "gf": int(sim["gf"][sim_idx, i]),
            "ga": int(sim["ga"][sim_idx, i]),
            "gd": int(sim["gd"][sim_idx, i]),
        })
    rows.sort(key=lambda r: r["position"])
    return rows


def notable_games(sim, sim_idx, matches, top_k=3):
    hg = sim["match_home_goals"][:, sim_idx]
    ag = sim["match_away_goals"][:, sim_idx]
    total = hg + ag
    margin = np.abs(hg.astype(int) - ag.astype(int))

    def pack(order):
        out = []
        for i in order[:top_k]:
            out.append({
                "home_team": matches[i]["home_team"], "away_team": matches[i]["away_team"],
                "home_goals": int(hg[i]), "away_goals": int(ag[i]), "date": matches[i]["date"],
            })
        return out

    return {
        "highest_scoring": pack(np.argsort(-total)),
        "biggest_wins": pack(np.argsort(-margin)),
    }


def pick_stories(sim, real_table, teams, matches):
    """Curate a handful of specific simulated seasons from the story batch,
    reusing the same categories (upsets, thrillers, hat-tricks) the rest of
    the pipeline already tracks -- not new invented dimensions. One example
    per category, and never the same champion team twice, so the curated
    set reads as distinct storylines rather than near-duplicate cards."""
    n_sims = sim["champion_idx"].shape[0]
    real_pos = {row["team"]: int(row["position"]) for _, row in real_table.iterrows()}
    champ_real_pos = np.array([real_pos[teams[i]] for i in sim["champion_idx"]])

    points_sorted = -np.sort(-sim["points"], axis=1)  # descending points per sim
    title_margin = points_sorted[:, 0] - points_sorted[:, 1]

    real_position_arr = np.array([real_pos[t] for t in teams])
    table_distance = np.abs(sim["position"] - real_position_arr[None, :]).sum(axis=1)

    champion_points = sim["points"][np.arange(n_sims), sim["champion_idx"]]

    categories = [
        ("biggest_upset", champ_real_pos, True),
        ("closest_title_race", title_margin, False),
        ("record_points_champion", champion_points, True),
        ("weakest_champion", champion_points, False),
        ("most_thrillers", sim["thriller_count"], True),
        ("most_hattricks", sim["hattrick_count"], True),
        ("closest_to_reality", table_distance, False),
        ("most_alternate_reality", table_distance, True),
    ]

    used_sims, used_champions = set(), set()
    stories = []
    for tag, arr, descending in categories:
        order = np.argsort(-arr if descending else arr)
        for sim_idx in order:
            sim_idx = int(sim_idx)
            champion = teams[sim["champion_idx"][sim_idx]]
            if sim_idx in used_sims or champion in used_champions:
                continue
            used_sims.add(sim_idx)
            used_champions.add(champion)
            stories.append({
                "sim": sim_idx,
                "tag": tag,
                "champion": champion,
                "champion_real_position": int(real_pos[champion]),
                "final_table": team_final_table(sim, sim_idx, teams),
                "notable_games": notable_games(sim, sim_idx, matches),
            })
            break
    return stories


def main():
    parser = argparse.ArgumentParser(description="Export treemap + story data for the PL title-race piece")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--teams-meta", required=True, help="JSON of {team: {slug, crest_file, color}}")
    parser.add_argument("--sims", type=int, default=1_000_000)
    parser.add_argument("--story-sims", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=20252026)
    parser.add_argument("--story-seed", type=int, default=20252027)
    parser.add_argument("--skip-big-pass", action="store_true",
                         help="Reuse an existing champions.bin in --out-dir instead of re-running the 1M-sim pass")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print(f"Loading shots from {args.shots} ...", file=sys.stderr)
    shots = load_shots(args.shots)
    real_table = build_real_table(shots)
    teams = sorted(real_table["team"].tolist())
    matches = build_match_index(shots)
    print(f"  {len(shots)} shots, {len(matches)} matches, {len(teams)} teams", file=sys.stderr)

    with open(args.teams_meta) as f:
        teams_meta = json.load(f)
    missing = [t for t in teams if t not in teams_meta]
    if missing:
        raise SystemExit(f"teams-meta is missing: {missing}")

    real_pos = {row["team"]: int(row["position"]) for _, row in real_table.iterrows()}
    team_idx = {t: i for i, t in enumerate(teams)}
    fixture_index = build_h2h_fixture_index(matches, team_idx)
    static_xg = static_match_xg(matches)

    champions_path = os.path.join(args.out_dir, "champions.bin")
    flagged_champions_path = os.path.join(args.out_dir, "flagged-champions.json")
    flagged_games_path = os.path.join(args.out_dir, "flagged-games.json")
    flagged_title_ties_path = os.path.join(args.out_dir, "flagged-title-ties.json")
    if args.skip_big_pass:
        print(f"\n=== Big pass: skipped, reusing {champions_path} ===", file=sys.stderr)
        champion_idx = np.fromfile(champions_path, dtype=np.uint8).astype(np.int64)
        title_counts = np.bincount(champion_idx, minlength=len(teams))
        # Flagged data isn't cached anywhere else -- reuse whatever's already
        # on disk from the last full run, if any, rather than wiping it out.
        flagged_champions = json.load(open(flagged_champions_path)) if os.path.exists(flagged_champions_path) else []
        flagged_games = json.load(open(flagged_games_path)) if os.path.exists(flagged_games_path) else []
        flagged_title_ties = json.load(open(flagged_title_ties_path)) if os.path.exists(flagged_title_ties_path) else []
        print(f"  reusing {len(flagged_champions)} flagged champions, {len(flagged_games)} flagged games, "
              f"{len(flagged_title_ties)} flagged title ties from disk", file=sys.stderr)
    else:
        print(f"\n=== Big pass, sweep 1: {args.sims:,} simulations ===", file=sys.stderr)
        t0 = time.time()
        sweep1 = run_big_pass_sweep1(matches, teams, args.sims, real_pos, seed=args.seed)
        print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

        print(f"\n=== Big pass, sweep 2: head-to-head ties + campaign logs ===", file=sys.stderr)
        t0 = time.time()
        sweep2 = run_big_pass_sweep2(matches, teams, args.sims, args.seed, team_idx, fixture_index,
                                      sweep1["pending_sims"], sweep1["flagged_champions"], static_xg)
        print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

        flagged_champions, flagged_title_ties = finalize_big_pass(
            sweep1, sweep2, teams, real_pos, fixture_index, args.seed)
        champion_idx = sweep1["champion_idx"]
        flagged_games = sweep1["flagged_games"]

        champion_idx.astype(np.uint8).tofile(champions_path)
        print(f"Wrote {args.sims:,} champion bytes to {champions_path}", file=sys.stderr)
        title_counts = np.bincount(champion_idx, minlength=len(teams))

        with open(flagged_champions_path, "w") as f:
            json.dump(flagged_champions, f, separators=(",", ":"))
        with open(flagged_games_path, "w") as f:
            json.dump(flagged_games, f, separators=(",", ":"))
        with open(flagged_title_ties_path, "w") as f:
            json.dump(flagged_title_ties, f, separators=(",", ":"))
        print(f"Wrote {len(flagged_champions):,} flagged champions to {flagged_champions_path} "
              f"({os.path.getsize(flagged_champions_path)/1024:.0f} KB)", file=sys.stderr)
        print(f"Wrote {len(flagged_games):,} flagged games to {flagged_games_path} "
              f"({os.path.getsize(flagged_games_path)/1024:.0f} KB)", file=sys.stderr)
        print(f"Wrote {len(flagged_title_ties):,} flagged title ties to {flagged_title_ties_path} "
              f"({os.path.getsize(flagged_title_ties_path)/1024:.0f} KB)", file=sys.stderr)

    print(f"\n=== Story pass: {args.story_sims:,} simulations (full detail) ===", file=sys.stderr)
    t0 = time.time()
    story_sim = run_simulation_with_matches(matches, teams, args.story_sims, seed=args.story_seed)
    apply_full_tiebreaks_to_batch(story_sim, fixture_index, args.story_seed)
    print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

    stories = pick_stories(story_sim, real_table, teams, matches)

    team_payload = []
    for i, t in enumerate(teams):
        team_payload.append({
            "team": t,
            **teams_meta[t],
            # This team's byte value in champions.bin -- teams there are
            # indexed by the alphabetical `teams` order used throughout this
            # script, which is *not* the title_count-descending order this
            # payload gets sorted into below. Ships explicitly so the client
            # can decode champions.bin / the flagged-sim files (which only
            # carry a global sim index) back to a team without having to
            # reproduce Python's sort order in JS.
            "champion_byte": i,
            "real_position": int(real_table[real_table["team"] == t]["position"].iloc[0]),
            "title_count": int(title_counts[i]),
            "title_odds": float(title_counts[i] / args.sims),
        })
    team_payload.sort(key=lambda r: -r["title_count"])

    real_champion = real_table.iloc[0]["team"]
    real_champion_idx = teams.index(real_champion)
    same_champion_odds = float(title_counts[real_champion_idx] / args.sims)

    payload = {
        "meta": {
            "n_sims": args.sims,
            "n_story_sims": args.story_sims,
            "n_teams": len(teams),
        },
        "real_table": real_table.to_dict(orient="records"),
        "same_champion_odds": same_champion_odds,
        "teams": team_payload,
        "stories": stories,
    }

    data_path = os.path.join(args.out_dir, "treemap-data.json")
    with open(data_path, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    size_kb = os.path.getsize(data_path) / 1024
    print(f"Wrote treemap data to {data_path} ({size_kb:.0f} KB)", file=sys.stderr)
    print(f"\n{len(stories)} curated stories:", file=sys.stderr)
    for s in stories:
        print(f"  [{s['tag']}] {s['champion']} (real pos {s['champion_real_position']})", file=sys.stderr)


if __name__ == "__main__":
    main()
