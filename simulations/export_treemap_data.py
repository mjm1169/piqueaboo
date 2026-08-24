"""
Build the data behind the "1,000,000 simulated seasons" title-race treemap.

Two separate simulation passes, at very different scales, feed two very
different outputs:

  1. A big, cheap pass (n_sims = --sims, meant to be run at ~1,000,000) that
     only needs to know, per simulation, WHO WON. That's exactly what
     run_simulation() from simulate_season.py already returns as
     champion_idx, so it's reused unmodified. The result is dumped as a
     compact binary file -- one byte per simulation, that byte being the
     champion's team index -- which is what actually drives the treemap:
     its layout (title count per team) and the fill colour of every pixel.

  2. A small, detailed pass (n_sims = --story-sims, a few thousand) that
     additionally keeps every match's scoreline for every one of its sims
     (affordable at this scale, not at 1,000,000). "Interesting" simulated
     seasons are picked out of *this* batch -- closest title races, biggest
     upset champions, etc -- each with a full final table and its own
     notable games, for the treemap's click-to-inspect stories.

  These two passes are intentionally not the same random draws. Every
  simulation is an independent, identically-distributed draw from the same
  model, so a "closest title race" example pulled from the small batch is
  just as genuine an illustration as one pulled from the big one would be
  -- there's no meaningful sense in which one specific one-in-a-million
  column is "more real" than a same-shaped example from a separate batch.
  Decoupling them like this is what keeps a 1,000,000-sim run affordable at
  all: the big pass never has to carry more than one byte per simulation.

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
    run_simulation,
)


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

    champions_path = os.path.join(args.out_dir, "champions.bin")
    if args.skip_big_pass:
        print(f"\n=== Big pass: skipped, reusing {champions_path} ===", file=sys.stderr)
        champion_idx = np.fromfile(champions_path, dtype=np.uint8).astype(np.int64)
        title_counts = np.bincount(champion_idx, minlength=len(teams))
    else:
        print(f"\n=== Big pass: {args.sims:,} simulations ===", file=sys.stderr)
        t0 = time.time()
        big = run_simulation(matches, teams, args.sims, seed=args.seed)
        print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

        big["champion_idx"].astype(np.uint8).tofile(champions_path)
        print(f"Wrote {args.sims:,} champion bytes to {champions_path}", file=sys.stderr)
        title_counts = np.bincount(big["champion_idx"], minlength=len(teams))

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
