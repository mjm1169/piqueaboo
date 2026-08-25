"""
Build the data behind the "1,000,000 simulated seasons" title-race treemap.

Two separate simulation passes, at very different scales, feed the outputs:

  1. The big pass (n_sims = --sims, meant to be run at ~1,000,000) is the
     spatial backbone of the treemap -- every one of its sims is a real,
     addressable cell -- and it applies a three-tier save policy per sim,
     cheapest tier first:
       - By default: just WHO WON. Dumped as a compact binary file, one
         byte per simulation (the champion's team index) -- this alone is
         what drives the treemap's layout (title count per team) and the
         fill colour of every cell.
       - If the champion's REAL-life finishing position was outside the
         top half of the table ("unexpected winner"): the sim's full final
         table is additionally kept (flagged-champions.json).
       - If any single match in that sim finished with a very high combined
         score, or one player scored a large individual haul: that match's
         full detail is additionally kept (flagged-games.json). A 6+-goal
         individual haul is capped to the single best-qualifying sim per
         real fixture (these turn out to cluster heavily on a handful of
         shot-heavy real matches, so keeping every raw hit would just be
         thousands of near-duplicates of the same few fixtures).
     All of this happens in one streaming pass over the matches (vectorised
     across all n_sims per match) -- the per-sim points/gf/ga totals needed
     for final standings are already carried through to the end regardless,
     so the "unexpected winner" tier costs nothing extra; the per-match
     threshold checks are cheap vectorised comparisons made while that
     match's goal arrays are already in scope, discarded once the loop
     moves to the next match.

  2. A small, separate, decoupled pass (n_sims = --story-sims, a few
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
     specific cell in the treemap grid.

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

import numpy as np

from simulate_season import (
    build_match_index,
    build_real_table,
    load_shots,
)


def run_big_pass_with_flags(matches, teams, n_sims, real_pos, seed=None,
                             high_score_threshold=15, haul_threshold=6):
    """
    The big (~1,000,000-sim) pass. Vectorised across all n_sims, one match
    at a time -- same streaming shape as run_simulation_with_matches below,
    but keeping only what the three-tier save policy actually needs:

      - points/gf/ga per sim, all the way through (already required to work
        out final standings/champion -- no extra cost for the "unexpected
        winner" tier).
      - per match, while its home/away goal arrays for all n_sims are still
        in scope: which sims cleared the high-scoring bar (kept as-is, no
        dedup -- rare enough already at this threshold), and the single
        best-qualifying sim for a 6+-goal individual haul (capped to one
        per real fixture -- see module docstring for why).

    Deliberately doesn't retain any full (n_matches, n_sims) match array --
    that's what makes 1,000,000 sims of full-detail-on-demand affordable at
    all. Once a match's iteration is done, only the handful of qualifying
    records for it survive.

    Returns champion_idx (for champions.bin / title counts) plus the two
    flagged-event lists, each entry tagged with its real global sim index
    so the client can place it in the actual treemap grid.
    """
    rng = np.random.default_rng(seed)
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}

    points = np.zeros((n_sims, n_teams), dtype=np.int32)
    gf = np.zeros((n_sims, n_teams), dtype=np.int32)
    ga = np.zeros((n_sims, n_teams), dtype=np.int32)

    flagged_games = []

    t0 = time.time()
    for i, m in enumerate(matches, 1):
        h_idx, a_idx = team_idx[m["home_team"]], team_idx[m["away_team"]]
        xg_h, xg_a = m["xg_h"], m["xg_a"]

        draws_h = rng.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        draws_a = rng.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)

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

        flagged_games.extend(match_flags.values())

        if i % 50 == 0 or i == len(matches):
            print(f"  [big pass] {i}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed, "
                  f"{len(flagged_games)} flagged games so far)", file=sys.stderr)

    gd = gf - ga
    rank_key = points.astype(np.int64) * 10_000_000 + (gd.astype(np.int64) + 500) * 10_000 + gf.astype(np.int64)
    order = np.argsort(-rank_key, axis=1)
    position = np.argsort(order, axis=1) + 1
    champion_idx = order[:, 0]

    # --- unexpected winners: every sim whose champion's real-life position
    # was outside the top half of the table gets its full final table kept ---
    champ_real_pos = np.array([real_pos[teams[i]] for i in champion_idx])
    upset_mask = champ_real_pos > (n_teams // 2)
    flagged_champions = []
    for s in np.flatnonzero(upset_mask).tolist():
        flagged_champions.append({
            "sim": s,
            "champion": teams[champion_idx[s]],
            "champion_real_position": int(champ_real_pos[s]),
            "final_table": build_final_table(points, gf, ga, position, s, teams),
        })

    return {
        "champion_idx": champion_idx,
        "flagged_champions": flagged_champions,
        "flagged_games": flagged_games,
    }


def build_final_table(points, gf, ga, position, sim_idx, teams):
    """Full final table for one sim, read straight out of the big pass's
    points/gf/ga/position arrays (kept for all n_sims regardless -- see
    run_big_pass_with_flags)."""
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

    champions_path = os.path.join(args.out_dir, "champions.bin")
    flagged_champions_path = os.path.join(args.out_dir, "flagged-champions.json")
    flagged_games_path = os.path.join(args.out_dir, "flagged-games.json")
    if args.skip_big_pass:
        print(f"\n=== Big pass: skipped, reusing {champions_path} ===", file=sys.stderr)
        champion_idx = np.fromfile(champions_path, dtype=np.uint8).astype(np.int64)
        title_counts = np.bincount(champion_idx, minlength=len(teams))
        # Flagged data isn't cached anywhere else -- reuse whatever's already
        # on disk from the last full run, if any, rather than wiping it out.
        flagged_champions = json.load(open(flagged_champions_path)) if os.path.exists(flagged_champions_path) else []
        flagged_games = json.load(open(flagged_games_path)) if os.path.exists(flagged_games_path) else []
        print(f"  reusing {len(flagged_champions)} flagged champions, {len(flagged_games)} flagged games from disk",
              file=sys.stderr)
    else:
        print(f"\n=== Big pass: {args.sims:,} simulations ===", file=sys.stderr)
        t0 = time.time()
        big = run_big_pass_with_flags(matches, teams, args.sims, real_pos, seed=args.seed)
        print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

        big["champion_idx"].astype(np.uint8).tofile(champions_path)
        print(f"Wrote {args.sims:,} champion bytes to {champions_path}", file=sys.stderr)
        title_counts = np.bincount(big["champion_idx"], minlength=len(teams))

        flagged_champions = big["flagged_champions"]
        flagged_games = big["flagged_games"]
        with open(flagged_champions_path, "w") as f:
            json.dump(flagged_champions, f, separators=(",", ":"))
        with open(flagged_games_path, "w") as f:
            json.dump(flagged_games, f, separators=(",", ":"))
        print(f"Wrote {len(flagged_champions):,} flagged champions to {flagged_champions_path} "
              f"({os.path.getsize(flagged_champions_path)/1024:.0f} KB)", file=sys.stderr)
        print(f"Wrote {len(flagged_games):,} flagged games to {flagged_games_path} "
              f"({os.path.getsize(flagged_games_path)/1024:.0f} KB)", file=sys.stderr)

    print(f"\n=== Story pass: {args.story_sims:,} simulations (full detail) ===", file=sys.stderr)
    t0 = time.time()
    story_sim = run_simulation_with_matches(matches, teams, args.story_sims, seed=args.story_seed)
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
