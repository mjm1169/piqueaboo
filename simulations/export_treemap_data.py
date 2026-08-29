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
    # Named win_count/draw_count/loss_count, not wins/draws/losses -- the
    # haul-detection loop below rebinds a plain `draws` as its own loop
    # variable (one of draws_h/draws_a per iteration), which would
    # otherwise silently shadow a same-named accumulator for the rest of
    # this function.
    win_count = np.zeros((n_sims, n_teams), dtype=np.int32)
    draw_count = np.zeros((n_sims, n_teams), dtype=np.int32)
    loss_count = np.zeros((n_sims, n_teams), dtype=np.int32)

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

        h_win = home_goals > away_goals
        a_win = away_goals > home_goals
        drawn = home_goals == away_goals
        points[:, h_idx] += np.where(h_win, 3, np.where(drawn, 1, 0))
        points[:, a_idx] += np.where(a_win, 3, np.where(drawn, 1, 0))
        gf[:, h_idx] += home_goals
        ga[:, h_idx] += away_goals
        gf[:, a_idx] += away_goals
        ga[:, a_idx] += home_goals
        win_count[:, h_idx] += h_win
        win_count[:, a_idx] += a_win
        draw_count[:, h_idx] += drawn
        draw_count[:, a_idx] += drawn
        loss_count[:, h_idx] += a_win
        loss_count[:, a_idx] += h_win

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
            "final_table": build_final_table(points, gf, ga, win_count, draw_count, loss_count, position, s, teams),
        }

    return {
        "points": points, "gf": gf, "ga": ga,
        "wins": win_count, "draws": draw_count, "losses": loss_count, "position": position,
        "champion_idx": champion_idx, "rank_key": rank_key,
        "flagged_champions": flagged_champions,
        "flagged_games": flagged_games,
        "pending_sims": pending_sims,
    }


def build_final_table(points, gf, ga, wins, draws, losses, position, sim_idx, teams):
    """Full final table for one sim, read straight out of the big pass's
    points/gf/ga/wins/draws/losses/position arrays (kept for all n_sims
    regardless -- see run_big_pass_sweep1)."""
    rows = []
    for i, t in enumerate(teams):
        rows.append({
            "team": t,
            "position": int(position[sim_idx, i]),
            "points": int(points[sim_idx, i]),
            "gf": int(gf[sim_idx, i]),
            "ga": int(ga[sim_idx, i]),
            "gd": int(gf[sim_idx, i] - ga[sim_idx, i]),
            "w": int(wins[sim_idx, i]),
            "d": int(draws[sim_idx, i]),
            "l": int(losses[sim_idx, i]),
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
    wins, draws, losses = sweep1["wins"], sweep1["draws"], sweep1["losses"]
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
        final_table = build_final_table(points, gf, ga, wins, draws, losses, position, sim, teams)

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


# =========================================================================
# CURATED TOUR: 9 hand-picked stories for the guided tour, each a specific
# real-world-flavoured extreme (fewest/no title wins, golden boot, closest
# title races, biggest/smallest margins, most teams tied for first) rather
# than "every qualifying sim" the way flagged-*.json is. Two of the nine
# (fewest wins, closest-by-tiebreak) come straight off data already on
# disk; the rest need per-sim tracking the big pass above never retains
# (a team's own position once folded into running totals; a season-long
# per-player goal tally). Both new sweeps below regenerate the *same*
# 1,000,000 sims bit-for-bit via the same _match_rng(seed, match_index)
# scheme sweep 1/2 already rely on -- champions.bin and the three
# flagged-*.json files are untouched, reused exactly as they already are.
# =========================================================================

def identify_final_matchday_indices(matches, n_teams):
    """Match indices for the real final matchday: the calendar date shared
    by exactly n_teams/2 matches (a real Premier League season always
    schedules every final-day fixture simultaneously) that's latest in the
    season. Confirmed against the real 2025/26 fixture list: exactly 10
    matches share the season's last date, 2026-05-24, with nothing else
    that late having anywhere near that many matches on one day."""
    by_date = defaultdict(list)
    for i, m in enumerate(matches):
        day = str(m["date"])[:10] if m["date"] else None
        by_date[day].append(i)
    expected = n_teams // 2
    candidates = [d for d, idxs in by_date.items() if len(idxs) == expected]
    if not candidates:
        raise ValueError(
            f"couldn't identify a final matchday: no date has exactly {expected} matches "
            f"(closest counts: {sorted((len(v) for v in by_date.values()), reverse=True)[:5]})"
        )
    final_date = max(candidates)
    return by_date[final_date], final_date


def run_table_metrics_sweep(matches, teams, n_sims, seed, final_day_indices):
    """
    Regenerates every match's draws (bit-identical to sweep 1/2, same
    per-match seeding) and accumulates two parallel points/gf/ga totals
    per sim per team: the full season, and the full season *minus* the
    final matchday -- the "table heading into the final gameweek" stops
    #2/#5/#6/#7/#8 below all derive from. Deliberately doesn't retain any
    full (n_matches, n_sims) match array, same discipline as sweep 1.
    """
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}
    final_day_set = set(final_day_indices)

    points = np.zeros((n_sims, n_teams), dtype=np.int32)
    gf = np.zeros((n_sims, n_teams), dtype=np.int32)
    ga = np.zeros((n_sims, n_teams), dtype=np.int32)
    wins = np.zeros((n_sims, n_teams), dtype=np.int32)
    draws = np.zeros((n_sims, n_teams), dtype=np.int32)
    losses = np.zeros((n_sims, n_teams), dtype=np.int32)
    points_pre = np.zeros((n_sims, n_teams), dtype=np.int32)
    gf_pre = np.zeros((n_sims, n_teams), dtype=np.int32)
    ga_pre = np.zeros((n_sims, n_teams), dtype=np.int32)
    wins_pre = np.zeros((n_sims, n_teams), dtype=np.int32)
    draws_pre = np.zeros((n_sims, n_teams), dtype=np.int32)
    losses_pre = np.zeros((n_sims, n_teams), dtype=np.int32)

    t0 = time.time()
    for i, m in enumerate(matches):
        h_idx, a_idx = team_idx[m["home_team"]], team_idx[m["away_team"]]
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, i)

        draws_h = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)
        home_goals = draws_h.sum(axis=1)
        away_goals = draws_a.sum(axis=1)

        h_win = home_goals > away_goals
        a_win = away_goals > home_goals
        drawn = home_goals == away_goals
        h_pts = np.where(h_win, 3, np.where(drawn, 1, 0))
        a_pts = np.where(a_win, 3, np.where(drawn, 1, 0))

        points[:, h_idx] += h_pts; points[:, a_idx] += a_pts
        gf[:, h_idx] += home_goals; ga[:, h_idx] += away_goals
        gf[:, a_idx] += away_goals; ga[:, a_idx] += home_goals
        wins[:, h_idx] += h_win; wins[:, a_idx] += a_win
        draws[:, h_idx] += drawn; draws[:, a_idx] += drawn
        losses[:, h_idx] += a_win; losses[:, a_idx] += h_win

        if i not in final_day_set:
            points_pre[:, h_idx] += h_pts; points_pre[:, a_idx] += a_pts
            gf_pre[:, h_idx] += home_goals; ga_pre[:, h_idx] += away_goals
            gf_pre[:, a_idx] += away_goals; ga_pre[:, a_idx] += home_goals
            wins_pre[:, h_idx] += h_win; wins_pre[:, a_idx] += a_win
            draws_pre[:, h_idx] += drawn; draws_pre[:, a_idx] += drawn
            losses_pre[:, h_idx] += a_win; losses_pre[:, a_idx] += h_win

        if (i + 1) % 50 == 0 or i + 1 == len(matches):
            print(f"  [table metrics sweep] {i+1}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed)",
                  file=sys.stderr)

    return {
        "points": points, "gf": gf, "ga": ga, "gd": gf - ga,
        "wins": wins, "draws": draws, "losses": losses,
        "points_pre": points_pre, "gf_pre": gf_pre, "ga_pre": ga_pre, "gd_pre": gf_pre - ga_pre,
        "wins_pre": wins_pre, "draws_pre": draws_pre, "losses_pre": losses_pre,
    }


def derive_table_stories(tm, champion_idx, teams, zero_win_teams):
    """
    Pure numpy derivation over the table-metrics sweep's output -- no I/O,
    no match regeneration -- picking out the specific sim each of stops
    #2/#5/#6/#7/#8 needs. `champion_idx` is the *existing*, already
    head-to-head-resolved champions.bin array, not re-derived here, so
    results stay consistent with the already-shipped title-tie
    resolution; position elsewhere in the table uses plain points/GD/GF
    ordering with no further tie-break, the same simplification already
    documented (and accepted) for run_big_pass_sweep1's own `position`.
    """
    n_sims, n_teams = tm["points"].shape
    points, gf, gd = tm["points"], tm["gf"], tm["gd"]

    rank_key = points.astype(np.int64) * 10_000_000 + (gd.astype(np.int64) + 500) * 10_000 + gf.astype(np.int64)
    order = np.argsort(-rank_key, axis=1)
    position = np.argsort(order, axis=1) + 1

    points_pre, gf_pre, gd_pre = tm["points_pre"], tm["gf_pre"], tm["gd_pre"]
    rank_key_pre = points_pre.astype(np.int64) * 10_000_000 + (gd_pre.astype(np.int64) + 500) * 10_000 + gf_pre.astype(np.int64)
    order_pre = np.argsort(-rank_key_pre, axis=1)
    position_pre = np.argsort(order_pre, axis=1) + 1

    # --- stop 2: no wins -- best (lowest) finish per zero-win team ---
    no_wins = {}
    for team in zero_win_teams:
        ti = teams.index(team)
        pos_col = position[:, ti]
        best_pos = int(pos_col.min())
        candidates = np.flatnonzero(pos_col == best_pos)
        best_sim = int(candidates[np.argmax(points[candidates, ti])])  # most decisive among ties
        no_wins[team] = {"sim": best_sim, "position": best_pos, "champion": teams[int(champion_idx[best_sim])]}

    # --- stop 8: most teams tied on points for first (points alone, not
    # the full points/GD/GF rank -- a plain points tie is far more common
    # than a full rank tie, which is all flagged-title-ties.json covers) ---
    top_points = points.max(axis=1)
    tie_count = (points == top_points[:, None]).sum(axis=1)
    most_tied_sim = int(np.argmax(tie_count))

    # --- stop 6: largest winning margin ---
    points_sorted = -np.sort(-points, axis=1)
    margin = points_sorted[:, 0] - points_sorted[:, 1]
    biggest_margin_sim = int(np.argmax(margin))

    # --- stop 7: lowest GD to win the league ---
    champ_gd = gd[np.arange(n_sims), champion_idx]
    lowest_gd_sim = int(np.argmin(champ_gd))

    # --- stop 5: closest title race heading into the final gameweek ---
    points_pre_sorted = -np.sort(-points_pre, axis=1)
    pre_margin = points_pre_sorted[:, 0] - points_pre_sorted[:, 1]
    closest_final_week_sim = int(np.argmin(pre_margin))

    return {
        "no_wins": no_wins,
        "most_tied_first": {"sim": most_tied_sim, "tie_count": int(tie_count[most_tied_sim]),
                             "champion": teams[int(champion_idx[most_tied_sim])]},
        "biggest_margin": {"sim": biggest_margin_sim, "margin": int(margin[biggest_margin_sim]),
                            "champion": teams[int(champion_idx[biggest_margin_sim])]},
        "lowest_gd": {"sim": lowest_gd_sim, "gd": int(champ_gd[lowest_gd_sim]),
                      "champion": teams[int(champion_idx[lowest_gd_sim])]},
        "closest_final_week": {"sim": closest_final_week_sim, "pre_margin": int(pre_margin[closest_final_week_sim]),
                                "champion": teams[int(champion_idx[closest_final_week_sim])]},
        "position": position, "position_pre": position_pre,
    }


def run_golden_boot_sweep(matches, teams, n_sims, seed, player_index, player_team):
    """
    Separate full-season regeneration accumulating per-*player* season
    goal totals for every sim -- something no other pass tracks at all
    (existing hat-trick/haul tracking is per-match, not summed across a
    player's whole season). `player_index`: player name -> row index (0..
    n_players-1) into the returned accumulator, covering every player who
    took at least one real shot this season -- can't prune to "plausible"
    scorers up front since stop #4 specifically wants the least-plausible
    simulated winner. int16 (not int8): safe headroom over any plausible
    single-season tally even though real per-player shot counts (max 125
    in this season's data) make an int8 overflow astronomically unlikely.
    """
    n_players = len(player_index)
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}
    season_goals = np.zeros((n_players, n_sims), dtype=np.int16)

    t0 = time.time()
    for i, m in enumerate(matches):
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, i)
        draws_h = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)

        for draws, players in ((draws_h, m["players_h"]), (draws_a, m["players_a"])):
            if draws.shape[1] == 0:
                continue
            for player in np.unique(players):
                cols = players == player
                season_goals[player_index[str(player)], :] += draws[:, cols].sum(axis=1).astype(np.int16)

        if (i + 1) % 50 == 0 or i + 1 == len(matches):
            print(f"  [golden boot sweep] {i+1}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed)",
                  file=sys.stderr)

    leader_idx = np.argmax(season_goals, axis=0)
    leader_goals = season_goals[leader_idx, np.arange(n_sims)]
    return {"leader_idx": leader_idx, "leader_goals": leader_goals}


def derive_golden_boot_stories(gb, player_names, real_goals_by_player):
    """Picks stop #3 (highest simulated golden boot total) and #4 (the
    simulated winner with the fewest *real-life* season goals -- tie-break
    prefers the higher simulated total, the more compelling of two
    equally-unexpected winners)."""
    leader_idx, leader_goals = gb["leader_idx"], gb["leader_goals"]
    n_sims = leader_idx.shape[0]

    highest_sim = int(np.argmax(leader_goals))

    real_goals_of_leader = np.array([real_goals_by_player.get(player_names[p], 0) for p in leader_idx])
    # ascending real goals, descending simulated goals as the tie-break
    order = np.lexsort((-leader_goals, real_goals_of_leader))
    most_unexpected_sim = int(order[0])

    def record(sim):
        p = player_names[int(leader_idx[sim])]
        return {"sim": sim, "player": p, "goals": int(leader_goals[sim]),
                "real_goals": int(real_goals_by_player.get(p, 0))}

    return {"highest": record(highest_sim), "most_unexpected": record(most_unexpected_sim)}


def build_campaign_for_sim(matches, seed, sim_idx, team, static_xg, n_sims):
    """Full 38-game campaign log (opponent, home/away, sim score, xG
    score) for one team in one specific sim -- a small targeted
    regeneration mirroring what run_big_pass_sweep2 already does in bulk
    for every flagged champion, just for one extra (sim, team) pair.

    Must request the *full* (n_sims, n_shots) shape, not a (sim_idx+1, ...)
    truncation: draws_h and draws_a are drawn sequentially from the same
    per-match rng_i, so draws_a's starting position in the random stream
    depends on how many values draws_h consumed -- which depends on the
    row count requested. Only a shape matching what champions.bin/the
    table-metrics sweep were built with (n_sims rows) lands on the same
    stream position and therefore the same bit-identical sim; a smaller
    shape silently reads a *different* (wrong) simulated season. Confirmed
    by direct reproduction: for sim_idx=88680, a (sim_idx+1, ...)-shaped
    regeneration disagreed with the full-shape sweep on 22/38 of Arsenal's
    matches."""
    campaign = []
    for i, m in enumerate(matches):
        is_home = m["home_team"] == team
        is_away = m["away_team"] == team
        if not (is_home or is_away):
            continue
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, i)
        draws_h = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)
        home_goals = int(draws_h[sim_idx].sum())
        away_goals = int(draws_a[sim_idx].sum())
        xg_home, xg_away = static_xg[i]
        opponent = m["away_team"] if is_home else m["home_team"]
        campaign.append({
            "opponent": opponent, "home": is_home, "date": m["date"],
            "sim_goals_for": home_goals if is_home else away_goals,
            "sim_goals_against": away_goals if is_home else home_goals,
            "xg_for": round(xg_home if is_home else xg_away, 2),
            "xg_against": round(xg_away if is_home else xg_home, 2),
        })
    return campaign


def build_final_matchday_detail(matches, seed, sim_idx, final_day_indices, n_sims):
    """Full scorelines + scorecards for every one of the final matchday's
    games, in one specific sim -- "what happened in the game week" for the
    closest-title-race-into-the-final-week story. Full (n_sims, ...) shape
    required -- see build_campaign_for_sim's docstring for why a truncated
    shape silently regenerates the wrong season."""
    games = []
    for i in final_day_indices:
        m = matches[i]
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, i)
        draws_h = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)
        scorers = (
            extract_scorecard(sim_idx, draws_h, m["players_h"], m["minutes_h"], m["is_pen_h"], m["home_team"])
            + extract_scorecard(sim_idx, draws_a, m["players_a"], m["minutes_a"], m["is_pen_a"], m["away_team"])
        )
        scorers.sort(key=lambda e: (e["minute"] is None, e["minute"]))
        games.append({
            "home_team": m["home_team"], "away_team": m["away_team"],
            "home_goals": int(draws_h[sim_idx].sum()), "away_goals": int(draws_a[sim_idx].sum()),
            "date": m["date"], "scorers": scorers,
        })
    return games


def build_best_match_for_player(matches, seed, sim_idx, player, team, n_sims):
    """This player's own highest-goal match within one specific sim, with
    a full scorecard -- the "game level detail" for a golden-boot story.
    Only checks matches where the player has at least one real shot on
    record (0 shots there trivially means 0 simulated goals too). Full
    (n_sims, ...) shape required -- see build_campaign_for_sim's
    docstring for why a truncated shape silently regenerates the wrong
    season."""
    best = None
    for i, m in enumerate(matches):
        is_home = m["home_team"] == team
        players = m["players_h"] if is_home else m["players_a"]
        if player not in players:
            continue
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, i)
        draws_h = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)
        own_draws = draws_h if is_home else draws_a
        own_players = m["players_h"] if is_home else m["players_a"]
        goals = int(own_draws[sim_idx, own_players == player].sum())
        if best is None or goals > best["goals"]:
            scorers = (
                extract_scorecard(sim_idx, draws_h, m["players_h"], m["minutes_h"], m["is_pen_h"], m["home_team"])
                + extract_scorecard(sim_idx, draws_a, m["players_a"], m["minutes_a"], m["is_pen_a"], m["away_team"])
            )
            scorers.sort(key=lambda e: (e["minute"] is None, e["minute"]))
            best = {
                "goals": goals, "home_team": m["home_team"], "away_team": m["away_team"],
                "home_goals": int(draws_h[sim_idx].sum()), "away_goals": int(draws_a[sim_idx].sum()),
                "date": m["date"], "scorers": scorers,
            }
    return best


def build_best_seasons(matches, teams, seed, static_xg, table_stories, zero_win_teams, tm, n_sims):
    """
    One full record per zero-title-win team -- Burnley/Sunderland/West
    Ham/Wolves on the current data -- their own best-ever simulated finish
    across the same 1,000,000 sims, feeding the roster's per-team cards for
    the clubs that never win outright (see
    notes/pl-xg-roster-card-candidates.md). All of the hard part
    (per-sim, per-team position, which the big pass in run_big_pass_sweep1
    discards once folded into running totals) already exists as a
    byproduct of the curated tour's own "no wins" stop --
    derive_table_stories's `no_wins` dict already holds every zero-win
    team's best position and which sim it happened in, not just the single
    one build_curated_tour picks for that one tour slot. This just adds
    each team's own full final table and 38-game campaign log (the latter
    via the same targeted build_campaign_for_sim() regeneration every
    other campaign-carrying record already relies on) and keeps all of
    them, not just the best-of-the-four.
    """
    records = []
    for team in zero_win_teams:
        rec = table_stories["no_wins"][team]
        sim = rec["sim"]
        final_table = build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"], table_stories["position"], sim, teams)
        campaign = build_campaign_for_sim(matches, seed, sim, team, static_xg, n_sims)
        records.append({
            "team": team, "sim": sim, "position": rec["position"], "champion": rec["champion"],
            "final_table": final_table, "campaign": campaign,
        })
    return records


# Editorial pick (see notes/pl-xg-roster-card-candidates.md): these clubs'
# second roster-card story is their own biggest-margin title win rather than
# a flagged game -- Tottenham's and Brighton's only flagged games are both
# defeats (conceding a 6-goal haul in Tottenham's case), so a flagged-game
# second story would read as unflattering for exactly the clubs that could
# most use a positive one. Everton joined this list rather than getting a
# golden-boot check (no flagged title-tie has them as champion either) --
# the user's call, a straightforward league win over the cost of a new
# per-club query on the golden-boot sweep. A fixed list, not a derived one:
# unlike zero_win_teams this isn't "every club with some property", it's a
# specific choice for these five.
OWN_BIGGEST_MARGIN_TEAMS = ["Tottenham", "Fulham", "Brighton", "Brentford", "Everton"]


def build_champion_margin_stories(matches, teams, seed, static_xg, tm, table_stories,
                                   champion_idx, real_pos, target_teams, n_sims):
    """
    For each of `target_teams`, their own biggest-margin title win: the
    largest points margin over the runner-up among just *that club's own*
    title-winning sims -- not the single global biggest-margin instance
    the curated tour's own `biggest_margin` stop already covers (Arsenal,
    on the current data). Reuses the same table-metrics sweep output
    (`tm`/`table_stories`) and already-shipped `champions.bin`
    (`champion_idx`) as build_best_seasons / the curated tour -- no extra
    sweep needed beyond what's already run for those. Record shape matches
    the curated tour's own `biggest_margin` stop exactly (same `kind` on
    the frontend, just a different team/sim), right down to the campaign
    being the *team's own* 38-game log, not anyone else's.
    """
    points = tm["points"]
    points_sorted = -np.sort(-points, axis=1)
    margin = points_sorted[:, 0] - points_sorted[:, 1]
    team_idx = {t: i for i, t in enumerate(teams)}

    records = []
    for team in target_teams:
        ti = team_idx[team]
        sims_as_champion = np.flatnonzero(champion_idx == ti)
        if sims_as_champion.size == 0:
            continue  # shouldn't happen for a team with title_count > 0, but don't crash if it ever does
        best_sim = int(sims_as_champion[np.argmax(margin[sims_as_champion])])
        final_table = build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"], table_stories["position"], best_sim, teams)
        campaign = build_campaign_for_sim(matches, seed, best_sim, team, static_xg, n_sims)
        records.append({
            "team": team, "sim": best_sim, "champion": team,
            "champion_real_position": int(real_pos[team]),
            "margin": int(margin[best_sim]),
            "final_table": final_table, "campaign": campaign,
        })
    return records


def build_curated_tour(matches, teams, title_counts, champion_idx, real_pos,
                        flagged_champions, flagged_title_ties, seed, static_xg,
                        final_day_indices, tm, table_stories, gb_stories, player_team, n_sims):
    """
    Assembles the 9 curated tour records. #1 (fewest wins) and #9 (closest
    by tiebreak) come straight from data the big pass already produced;
    #2/#5/#6/#7/#8 come from the table-metrics sweep's derived stories
    (`table_stories`, from derive_table_stories); #3/#4 from the golden
    boot sweep's derived stories (`gb_stories`). Each of the latter needs
    one small targeted regeneration for its own game/campaign detail --
    see build_campaign_for_sim / build_final_matchday_detail /
    build_best_match_for_player above -- data-only; presentation (modal
    copy, captions) is entirely the frontend's job, same split as every
    other flagged-sim record already shipped.
    """
    tour = []

    # --- 1: fewest wins ---
    nonzero = [(t, int(c)) for t, c in zip(teams, title_counts) if c > 0]
    fewest_team, fewest_count = min(nonzero, key=lambda x: x[1])
    fewest_example = next(c for c in flagged_champions if c["champion"] == fewest_team)
    tour.append({
        "kind": "fewest_wins", "sim": fewest_example["sim"], "champion": fewest_team,
        "champion_real_position": fewest_example["champion_real_position"],
        "title_count": fewest_count,
        "final_table": fewest_example["final_table"], "campaign": fewest_example["campaign"],
    })

    # --- 2: no wins -- whichever zero-win team's own best-ever finish is
    # the highest position among the (up to 4) zero-win teams ---
    zero_win_teams = [t for t, c in zip(teams, title_counts) if c == 0]
    best_team = min(zero_win_teams, key=lambda t: table_stories["no_wins"][t]["position"])
    rec = table_stories["no_wins"][best_team]
    final_table = build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"], table_stories["position"], rec["sim"], teams)
    tour.append({
        "kind": "no_wins", "sim": rec["sim"], "team": best_team, "position": rec["position"],
        "champion": rec["champion"], "final_table": final_table,
    })

    # --- 3 & 4: golden boot -- game-by-game detail for the scorer's own
    # team, same targeted build_campaign_for_sim() every other
    # campaign-carrying record already relies on ---
    for key, kind in (("highest", "golden_boot"), ("most_unexpected", "unexpected_golden_boot")):
        g = gb_stories[key]
        team = player_team.get(g["player"], teams[int(champion_idx[g["sim"]])])
        match = build_best_match_for_player(matches, seed, g["sim"], g["player"], team, n_sims)
        campaign = build_campaign_for_sim(matches, seed, g["sim"], team, static_xg, n_sims)
        tour.append({
            "kind": kind, "sim": g["sim"], "player": g["player"], "team": team,
            "goals": g["goals"], "real_goals": g["real_goals"], "match": match, "campaign": campaign,
        })

    # --- 5: closest race into the final week ---
    r5 = table_stories["closest_final_week"]
    table_after = build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"], table_stories["position"], r5["sim"], teams)
    table_before = build_final_table(tm["points_pre"], tm["gf_pre"], tm["ga_pre"], tm["wins_pre"], tm["draws_pre"], tm["losses_pre"], table_stories["position_pre"], r5["sim"], teams)
    games = build_final_matchday_detail(matches, seed, r5["sim"], final_day_indices, n_sims)
    tour.append({
        "kind": "closest_final_week", "sim": r5["sim"], "champion": r5["champion"],
        "pre_margin": r5["pre_margin"], "table_before": table_before, "final_table": table_after,
        "games": games,
    })

    # --- 6: largest winning margin ---
    r6 = table_stories["biggest_margin"]
    tour.append({
        "kind": "biggest_margin", "sim": r6["sim"], "champion": r6["champion"],
        "champion_real_position": real_pos[r6["champion"]], "margin": r6["margin"],
        "final_table": build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"], table_stories["position"], r6["sim"], teams),
        "campaign": build_campaign_for_sim(matches, seed, r6["sim"], r6["champion"], static_xg, n_sims),
    })

    # --- 7: lowest GD to win ---
    r7 = table_stories["lowest_gd"]
    tour.append({
        "kind": "lowest_gd", "sim": r7["sim"], "champion": r7["champion"],
        "champion_real_position": real_pos[r7["champion"]], "gd": r7["gd"],
        "final_table": build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"], table_stories["position"], r7["sim"], teams),
        "campaign": build_campaign_for_sim(matches, seed, r7["sim"], r7["champion"], static_xg, n_sims),
    })

    # --- 8: most teams tied on points for first ---
    r8 = table_stories["most_tied_first"]
    tour.append({
        "kind": "most_tied_first", "sim": r8["sim"], "champion": r8["champion"], "tie_count": r8["tie_count"],
        "final_table": build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"], table_stories["position"], r8["sim"], teams),
    })

    # --- 9: closest by head-to-head / away goals -- prefer the deeper
    # (away-goals) tiebreak as the "closest" of the two. Title-level ties
    # are rare (~30 per million sims per the big-pass docstring), so a
    # small dry run can legitimately produce zero -- that's not a bug, just
    # not enough sims yet, so skip the stop rather than crash. At the real
    # 1,000,000-sim scale this list is never empty in practice.
    if flagged_title_ties:
        by_depth = sorted(flagged_title_ties, key=lambda t: t["resolution"] != "h2h_away_goals")
        closest_tie = by_depth[0]
        tour.append({"kind": "closest_tiebreak", **closest_tie})
    else:
        print("  WARNING: no flagged title ties available -- skipping stop 9 "
              "(closest_tiebreak). Expected at small --sims counts; must not "
              "happen on the real 1,000,000-sim run.", file=sys.stderr)

    return tour


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
    parser.add_argument("--skip-curated-tour", action="store_true",
                         help="Reuse an existing curated-tour.json in --out-dir instead of re-running the "
                              "table-metrics/golden-boot sweeps")
    parser.add_argument("--skip-best-seasons", action="store_true",
                         help="Reuse an existing best-seasons.json in --out-dir instead of rebuilding it")
    parser.add_argument("--skip-champion-margin-stories", action="store_true",
                         help="Reuse an existing champion-margin-stories.json in --out-dir instead of rebuilding it")
    parser.add_argument("--skip-story-pass", action="store_true",
                         help="Skip the small 20,000-sim story-batch pass, leaving treemap-data.json untouched "
                              "on disk instead of rewriting it (the pass is otherwise unconditional)")
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

    curated_tour_path = os.path.join(args.out_dir, "curated-tour.json")
    best_seasons_path = os.path.join(args.out_dir, "best-seasons.json")
    champion_margin_stories_path = os.path.join(args.out_dir, "champion-margin-stories.json")
    zero_win_teams = [t for i, t in enumerate(teams) if title_counts[i] == 0]

    # The table-metrics sweep (per-sim, per-team running position -- the one
    # thing the big pass discards) feeds the curated tour's "no wins" stop,
    # every zero-win team's own best-seasons.json record, and the editorial
    # champion-margin-stories.json picks below, so it only gets skipped when
    # none of the three outputs are wanted this run.
    tm = table_stories = final_day_indices = None
    if args.skip_curated_tour and args.skip_best_seasons and args.skip_champion_margin_stories:
        print(f"\n=== Table-metrics sweep: skipped, reusing {curated_tour_path} / "
              f"{best_seasons_path} / {champion_margin_stories_path} ===", file=sys.stderr)
    else:
        print(f"\n=== Table-metrics sweep: {args.sims:,} simulations ===", file=sys.stderr)
        final_day_indices, final_date = identify_final_matchday_indices(matches, len(teams))
        print(f"  final matchday identified as {final_date} ({len(final_day_indices)} matches)", file=sys.stderr)

        t0 = time.time()
        tm = run_table_metrics_sweep(matches, teams, args.sims, args.seed, final_day_indices)
        print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

        table_stories = derive_table_stories(tm, champion_idx, teams, zero_win_teams)

    if args.skip_best_seasons:
        print(f"\n=== Best seasons: skipped, reusing {best_seasons_path} ===", file=sys.stderr)
    else:
        print(f"\n=== Best seasons: {len(zero_win_teams)} zero-win team(s) ===", file=sys.stderr)
        best_seasons = build_best_seasons(matches, teams, args.seed, static_xg, table_stories,
                                           zero_win_teams, tm, args.sims)
        with open(best_seasons_path, "w") as f:
            json.dump(best_seasons, f, separators=(",", ":"))
        print(f"Wrote {len(best_seasons)} best-season record(s) to {best_seasons_path} "
              f"({os.path.getsize(best_seasons_path)/1024:.0f} KB)", file=sys.stderr)
        for r in best_seasons:
            print(f"  [{r['team']}] best-ever position {r['position']} (sim #{r['sim']:,})", file=sys.stderr)

    if args.skip_champion_margin_stories:
        print(f"\n=== Champion margin stories: skipped, reusing {champion_margin_stories_path} ===", file=sys.stderr)
    else:
        print(f"\n=== Champion margin stories: {len(OWN_BIGGEST_MARGIN_TEAMS)} club(s) ===", file=sys.stderr)
        champion_margin_stories = build_champion_margin_stories(
            matches, teams, args.seed, static_xg, tm, table_stories,
            champion_idx, real_pos, OWN_BIGGEST_MARGIN_TEAMS, args.sims)
        with open(champion_margin_stories_path, "w") as f:
            json.dump(champion_margin_stories, f, separators=(",", ":"))
        print(f"Wrote {len(champion_margin_stories)} champion-margin record(s) to {champion_margin_stories_path} "
              f"({os.path.getsize(champion_margin_stories_path)/1024:.0f} KB)", file=sys.stderr)
        for r in champion_margin_stories:
            print(f"  [{r['team']}] biggest title-winning margin {r['margin']} pts (sim #{r['sim']:,})", file=sys.stderr)

    if args.skip_curated_tour:
        print(f"\n=== Curated tour: skipped, reusing {curated_tour_path} ===", file=sys.stderr)
    else:
        # Player index/team/real-season-goals, built once from the real
        # shots data -- no per-sim work here, just a lookup the golden
        # boot sweep and the curated-tour assembly both need.
        all_players = sorted(shots["player"].dropna().unique().tolist())
        player_index = {p: i for i, p in enumerate(all_players)}
        player_team = {}
        for _, row in shots.drop_duplicates("player").iterrows():
            player_team[row["player"]] = row["h_team"] if row["h_a"] == "h" else row["a_team"]
        real_goals_by_player = shots[shots["result"] == "Goal"].groupby("player").size().to_dict()

        print(f"\n=== Curated tour: golden-boot sweep, {args.sims:,} simulations, "
              f"{len(all_players)} players ===", file=sys.stderr)
        t0 = time.time()
        gb = run_golden_boot_sweep(matches, teams, args.sims, args.seed, player_index, player_team)
        print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)
        gb_stories = derive_golden_boot_stories(gb, all_players, real_goals_by_player)

        curated_tour = build_curated_tour(
            matches, teams, title_counts, champion_idx, real_pos,
            flagged_champions, flagged_title_ties, args.seed, static_xg,
            final_day_indices, tm, table_stories, gb_stories, player_team, args.sims,
        )
        with open(curated_tour_path, "w") as f:
            json.dump(curated_tour, f, separators=(",", ":"))
        print(f"Wrote {len(curated_tour)} curated tour stops to {curated_tour_path} "
              f"({os.path.getsize(curated_tour_path)/1024:.0f} KB)", file=sys.stderr)
        for stop in curated_tour:
            print(f"  [{stop['kind']}] sim #{stop['sim']:,}", file=sys.stderr)

    data_path = os.path.join(args.out_dir, "treemap-data.json")
    if args.skip_story_pass:
        print(f"\n=== Story pass: skipped, leaving {data_path} untouched ===", file=sys.stderr)
        return

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

    with open(data_path, "w") as f:
        json.dump(payload, f, separators=(",", ":"))
    size_kb = os.path.getsize(data_path) / 1024
    print(f"Wrote treemap data to {data_path} ({size_kb:.0f} KB)", file=sys.stderr)
    print(f"\n{len(stories)} curated stories:", file=sys.stderr)
    for s in stories:
        print(f"  [{s['tag']}] {s['champion']} (real pos {s['champion_real_position']})", file=sys.stderr)


if __name__ == "__main__":
    main()
