"""
Monte Carlo re-simulation of a Premier League season from shot-by-shot xG.

The idea: every shot in the real season had some probability of being a
goal (its xG). What actually happened was one draw from that process. This
script re-runs the season N times, each time re-rolling every single shot
as an independent Bernoulli(xG) trial, and rebuilds the resulting league
table, match results, and notable individual/team performances.

This deliberately simplifies real football in a few ways, worth stating up
front:
  - Shots are treated as independent of each other (no momentum, game
    state, fatigue, or subs effects; a team 4-0 up doesn't shoot differently).
  - Own goals aren't modelled (Understat doesn't attribute an xG to them).
That's fine for the story being told here (how much of a season's shape
comes from "who created the better chances" vs. "how the coin landed on
each one") rather than a forecasting tool.

Tie-breaking uses the real Premier League chain -- points, goal difference,
goals scored, head-to-head points, head-to-head away goals, then a random
coin flip standing in for the real world's final "play-off at a neutral
venue" -- via resolve_tied_group() below, wherever a caller has the full
match-by-match results needed to compute it (this module's own
run_simulation() doesn't retain per-match results across all its sims, so
it still falls back to points/GD/GF only; callers that do keep per-sim
match detail should use resolve_tied_group() for a correct table).

Usage:
    python simulate_season.py --shots data/shots_2024_25.csv --sims 200 \
        --out results/sim_test.json

Output is one JSON file: the real (actual) table for reference, the
simulated title odds / average finishing position per team, and a handful
of "showcase" extremes (highest-scoring simulated matches, biggest
individual match hauls, most surprising simulated champions) pulled out
across all simulations.
"""

import argparse
import json
import sys
import time

import numpy as np
import pandas as pd


def load_shots(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"match_id", "h_a", "xG", "player", "h_team", "a_team", "h_goals", "a_goals"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"shots file is missing expected columns: {missing}")
    df["xG"] = pd.to_numeric(df["xG"], errors="coerce").fillna(0.0).clip(0, 1)
    return df


def build_real_table(shots: pd.DataFrame) -> pd.DataFrame:
    """Actual final standings, computed from the real match scorelines."""
    matches = shots.drop_duplicates("match_id")[
        ["match_id", "h_team", "a_team", "h_goals", "a_goals"]
    ].copy()
    matches["h_goals"] = matches["h_goals"].astype(int)
    matches["a_goals"] = matches["a_goals"].astype(int)

    teams = sorted(set(matches["h_team"]) | set(matches["a_team"]))
    table = {t: {"points": 0, "gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0} for t in teams}

    for _, m in matches.iterrows():
        h, a, hg, ag = m["h_team"], m["a_team"], m["h_goals"], m["a_goals"]
        table[h]["gf"] += hg
        table[h]["ga"] += ag
        table[a]["gf"] += ag
        table[a]["ga"] += hg
        if hg > ag:
            table[h]["points"] += 3
            table[h]["w"] += 1
            table[a]["l"] += 1
        elif ag > hg:
            table[a]["points"] += 3
            table[a]["w"] += 1
            table[h]["l"] += 1
        else:
            table[h]["points"] += 1
            table[a]["points"] += 1
            table[h]["d"] += 1
            table[a]["d"] += 1

    rows = []
    for t, s in table.items():
        rows.append({"team": t, "gd": s["gf"] - s["ga"], **s})
    out = pd.DataFrame(rows).sort_values(
        ["points", "gd", "gf"], ascending=False
    ).reset_index(drop=True)
    out["position"] = out.index + 1
    return out


def build_match_index(shots: pd.DataFrame):
    """
    Group shots into a per-match structure ready for vectorised simulation:
    each match keeps its home/away team names and, per side, the xG and
    scoring player for every shot -- plus each shot's minute and whether it
    was a penalty (situation == "Penalty"), aligned by index alongside the
    player arrays, for building full scorecards ("Haaland (1', 31', 54'
    (p))") when a match is flagged as notable.
    """
    matches = []
    for match_id, g in shots.groupby("match_id", sort=False):
        h_shots = g[g["h_a"] == "h"]
        a_shots = g[g["h_a"] == "a"]
        matches.append({
            "match_id": match_id,
            "home_team": g["h_team"].iloc[0],
            "away_team": g["a_team"].iloc[0],
            "date": g["date"].iloc[0] if "date" in g.columns else None,
            "xg_h": h_shots["xG"].to_numpy(dtype=float),
            "xg_a": a_shots["xG"].to_numpy(dtype=float),
            "players_h": h_shots["player"].to_numpy(),
            "players_a": a_shots["player"].to_numpy(),
            "minutes_h": h_shots["minute"].to_numpy(dtype=int) if "minute" in g.columns else None,
            "minutes_a": a_shots["minute"].to_numpy(dtype=int) if "minute" in g.columns else None,
            "is_pen_h": (h_shots["situation"] == "Penalty").to_numpy() if "situation" in g.columns else None,
            "is_pen_a": (a_shots["situation"] == "Penalty").to_numpy() if "situation" in g.columns else None,
        })
    return matches


def build_h2h_fixture_index(matches, team_idx):
    """
    {frozenset({team_a_idx, team_b_idx}): [(match_index, home_idx, away_idx), ...]}
    for every pair of teams -- each pair maps to exactly two matches (their
    home-and-away fixtures) in a standard double round-robin. Static, built
    once from the real fixture list; independent of any simulation.
    """
    fixtures = {}
    for i, m in enumerate(matches):
        h, a = team_idx[m["home_team"]], team_idx[m["away_team"]]
        fixtures.setdefault(frozenset((h, a)), []).append((i, h, a))
    return fixtures


def resolve_tied_group(tied_idxs, fixture_index, get_result, rng=None):
    """
    Resolve a group of team indices tied on points/GD/GF, using the real
    Premier League chain: a head-to-head mini-league's points among just
    the tied teams; if still tied, head-to-head away goals among whichever
    subset remains tied; if still tied, a coin flip (standing in for a
    real-world play-off at a neutral venue).

    fixture_index: from build_h2h_fixture_index().
    get_result(match_index) -> (home_goals, away_goals) for the ONE sim
    being resolved -- the caller supplies this however it has the data
    (a retained match matrix, or a handful of specifically-gathered results).
    rng: a numpy Generator used only for the coin-flip stage, so the whole
    pipeline stays reproducible under a fixed seed like everything else
    here -- pass the same seeded Generator callers already use elsewhere.
    Defaults to an unseeded one (genuinely random) if not given.

    Returns (ordered_idxs, criterion), best-placed first. criterion is
    'none' (no tie), 'h2h_points', 'h2h_away_goals', or 'coin_flip' --
    whichever was the *most* severe stage actually needed anywhere in the
    group (a single group can contain more than two teams, and different
    subsets can resolve at different stages).
    """
    if len(tied_idxs) < 2:
        return list(tied_idxs), "none"
    if rng is None:
        rng = np.random.default_rng()

    def h2h_points_table(idxs):
        pts = {t: 0 for t in idxs}
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                a, b = idxs[i], idxs[j]
                for match_idx, home_idx, _away_idx in fixture_index.get(frozenset((a, b)), []):
                    hg, ag = get_result(match_idx)
                    a_goals, b_goals = (hg, ag) if home_idx == a else (ag, hg)
                    if a_goals > b_goals:
                        pts[a] += 3
                    elif b_goals > a_goals:
                        pts[b] += 3
                    else:
                        pts[a] += 1
                        pts[b] += 1
        return pts

    def h2h_away_table(idxs):
        away = {t: 0 for t in idxs}
        for i in range(len(idxs)):
            for j in range(i + 1, len(idxs)):
                a, b = idxs[i], idxs[j]
                for match_idx, _home_idx, away_idx in fixture_index.get(frozenset((a, b)), []):
                    _hg, ag = get_result(match_idx)
                    away[away_idx] += ag
        return away

    def group_by(idxs, key_fn):
        ordered = sorted(idxs, key=lambda t: -key_fn(t))
        groups, current = [], [ordered[0]]
        for t in ordered[1:]:
            if key_fn(t) == key_fn(current[-1]):
                current.append(t)
            else:
                groups.append(current)
                current = [t]
        groups.append(current)
        return groups

    pts = h2h_points_table(tied_idxs)
    groups = group_by(tied_idxs, lambda t: pts[t])

    final_order = []
    criterion = "h2h_points"
    for g in groups:
        if len(g) == 1:
            final_order.extend(g)
            continue
        away = h2h_away_table(g)
        subgroups = group_by(g, lambda t: away[t])
        if len(subgroups) > 1:
            criterion = "h2h_away_goals"
        for sg in subgroups:
            if len(sg) == 1:
                final_order.extend(sg)
            else:
                criterion = "coin_flip"
                shuffled = list(sg)
                rng.shuffle(shuffled)
                final_order.extend(shuffled)
    return final_order, criterion


def run_simulation(matches, teams, n_sims, seed=None, thriller_threshold=7, hattrick_threshold=3):
    rng = np.random.default_rng(seed)
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}

    points = np.zeros((n_sims, n_teams), dtype=np.int32)
    gf = np.zeros((n_sims, n_teams), dtype=np.int32)
    ga = np.zeros((n_sims, n_teams), dtype=np.int32)

    thriller_count = np.zeros(n_sims, dtype=np.int32)     # matches >= threshold goals, per sim
    hattrick_count = np.zeros(n_sims, dtype=np.int32)     # player games >= threshold goals, per sim
    total_goals_sum = np.zeros(n_sims, dtype=np.int64)    # sanity check / "goals per season"

    # "showcase" extremes: cheapest to just track one best-sim-per-match/
    # match-and-player rather than a true global top-K across all N*380
    # (match, sim) pairs -- see module docstring for why that's an
    # acceptable simplification for a highlights list.
    showcase_matches = []   # one entry per match: its single highest-scoring sim
    showcase_wins = []      # one entry per match: its single biggest-margin sim
    showcase_players = []   # one entry per (match, player): its best sim, if >= hattrick_threshold

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

        total = home_goals + away_goals
        total_goals_sum += total
        thriller_count += (total >= thriller_threshold)

        best_sim = int(np.argmax(total))
        showcase_matches.append({
            "home_team": m["home_team"], "away_team": m["away_team"],
            "home_goals": int(home_goals[best_sim]), "away_goals": int(away_goals[best_sim]),
            "total_goals": int(total[best_sim]), "sim": best_sim, "date": m["date"],
        })

        margin = np.abs(home_goals - away_goals)
        best_margin_sim = int(np.argmax(margin))
        showcase_wins.append({
            "home_team": m["home_team"], "away_team": m["away_team"],
            "home_goals": int(home_goals[best_margin_sim]), "away_goals": int(away_goals[best_margin_sim]),
            "margin": int(margin[best_margin_sim]), "sim": best_margin_sim, "date": m["date"],
        })

        for side_name, draws, players in (("h", draws_h, m["players_h"]), ("a", draws_a, m["players_a"])):
            if draws.shape[1] == 0:
                continue
            for player in pd.unique(players):
                cols = players == player
                player_goals = draws[:, cols].sum(axis=1)
                hattrick_count += (player_goals >= hattrick_threshold)
                best = int(np.argmax(player_goals))
                if player_goals[best] >= hattrick_threshold:
                    showcase_players.append({
                        "player": str(player),
                        "team": m["home_team"] if side_name == "h" else m["away_team"],
                        "opponent": m["away_team"] if side_name == "h" else m["home_team"],
                        "goals": int(player_goals[best]), "sim": best, "date": m["date"],
                    })

        if i % 50 == 0 or i == len(matches):
            print(f"  simulated {i}/{len(matches)} matches ({time.time()-t0:.1f}s elapsed)", file=sys.stderr)

    gd = gf - ga
    # Rank key: points dominate, then GD, then GF -- scaled so higher-priority
    # terms can never be overturned by lower-priority ones, then sorted
    # descending per simulation in one vectorised pass.
    rank_key = points.astype(np.int64) * 10_000_000 + (gd.astype(np.int64) + 500) * 10_000 + gf.astype(np.int64)
    order = np.argsort(-rank_key, axis=1)              # order[s, k] = team index finishing at rank k+1 in sim s
    position = np.argsort(order, axis=1) + 1            # position[s, t] = finishing rank of team t in sim s

    champion_idx = order[:, 0]
    champion_points = points[np.arange(n_sims), champion_idx]

    return {
        "teams": teams,
        "points": points, "gf": gf, "ga": ga, "gd": gd, "position": position,
        "champion_idx": champion_idx, "champion_points": champion_points,
        "thriller_count": thriller_count, "hattrick_count": hattrick_count,
        "total_goals_sum": total_goals_sum,
        "showcase_matches": showcase_matches, "showcase_wins": showcase_wins,
        "showcase_players": showcase_players,
    }


def summarise(sim, real_table, n_sims, thriller_threshold, hattrick_threshold, top_k=15):
    teams = sim["teams"]
    n_teams = len(teams)
    real_pos = {row["team"]: int(row["position"]) for _, row in real_table.iterrows()}

    per_team = []
    for i, t in enumerate(teams):
        pos_counts = np.bincount(sim["position"][:, i] - 1, minlength=n_teams)
        per_team.append({
            "team": t,
            "real_position": real_pos[t],
            "title_odds": float((sim["champion_idx"] == i).mean()),
            "avg_position": float(sim["position"][:, i].mean()),
            "avg_points": float(sim["points"][:, i].mean()),
            "points_p10": float(np.percentile(sim["points"][:, i], 10)),
            "points_p90": float(np.percentile(sim["points"][:, i], 90)),
            "position_distribution": pos_counts.tolist(),  # index 0 = 1st place count, etc.
        })
    per_team.sort(key=lambda r: -r["title_odds"])

    # "Minnows winning the title": simulations where the champion's REAL
    # finishing position was outside the top half of the table.
    champ_real_pos = np.array([real_pos[teams[i]] for i in sim["champion_idx"]])
    upset_mask = champ_real_pos > n_teams // 2
    upset_sims = np.where(upset_mask)[0]
    worst_upsets = sorted(
        ({"sim": int(s), "champion": teams[sim["champion_idx"][s]],
          "real_position": int(champ_real_pos[s]),
          "simulated_points": int(sim["champion_points"][s])} for s in upset_sims),
        key=lambda r: -r["real_position"],
    )[:top_k]

    showcase_matches = sorted(sim["showcase_matches"], key=lambda r: -r["total_goals"])[:top_k]
    showcase_wins = sorted(sim["showcase_wins"], key=lambda r: -r["margin"])[:top_k]
    showcase_players = sorted(sim["showcase_players"], key=lambda r: -r["goals"])[:top_k]

    return {
        "meta": {
            "n_sims": n_sims,
            "n_teams": n_teams,
            "n_matches": len(sim["showcase_matches"]),
            "thriller_threshold_goals": thriller_threshold,
            "hattrick_threshold_goals": hattrick_threshold,
            "real_avg_goals_per_game": None,  # filled in by caller
        },
        "real_table": real_table.to_dict(orient="records"),
        "per_team": per_team,
        "same_champion_odds": float((np.array([teams[i] for i in sim["champion_idx"]])
                                      == real_table.iloc[0]["team"]).mean()),
        "upset_titles": {
            "count": int(upset_mask.sum()),
            "probability": float(upset_mask.mean()),
            "examples": worst_upsets,
        },
        "thrillers": {
            "avg_per_season": float(sim["thriller_count"].mean()),
            "max_in_a_season": int(sim["thriller_count"].max()),
            "examples": showcase_matches,
        },
        "biggest_wins": {
            "examples": showcase_wins,
        },
        "hattricks": {
            "avg_per_season": float(sim["hattrick_count"].mean()),
            "max_in_a_season": int(sim["hattrick_count"].max()),
            "examples": showcase_players,
        },
        "goals": {
            "avg_total_per_season": float(sim["total_goals_sum"].mean()),
            "avg_per_game": float(sim["total_goals_sum"].mean() / len(sim["showcase_matches"])),
        },
        "champion_points": {
            "avg": float(sim["champion_points"].mean()),
            "min": int(sim["champion_points"].min()),
            "max": int(sim["champion_points"].max()),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo re-simulate a season from shot xG")
    parser.add_argument("--shots", required=True, help="Path to scraped shots CSV")
    parser.add_argument("--sims", type=int, default=200, help="Number of simulated seasons")
    parser.add_argument("--out", required=True, help="Output JSON path")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for reproducibility")
    parser.add_argument("--thriller-threshold", type=int, default=7, help="Total goals in a match to count as a thriller")
    parser.add_argument("--hattrick-threshold", type=int, default=3, help="Goals in a match to count as a 'big haul'")
    args = parser.parse_args()

    print(f"Loading shots from {args.shots} ...", file=sys.stderr)
    shots = load_shots(args.shots)
    print(f"  {len(shots)} shots across {shots['match_id'].nunique()} matches", file=sys.stderr)

    real_table = build_real_table(shots)
    teams = sorted(real_table["team"].tolist())
    matches = build_match_index(shots)

    print(f"Running {args.sims} simulations ...", file=sys.stderr)
    t0 = time.time()
    sim = run_simulation(
        matches, teams, args.sims, seed=args.seed,
        thriller_threshold=args.thriller_threshold,
        hattrick_threshold=args.hattrick_threshold,
    )
    print(f"Done in {time.time()-t0:.1f}s", file=sys.stderr)

    summary = summarise(sim, real_table, args.sims, args.thriller_threshold, args.hattrick_threshold)
    real_goals = real_table["gf"].sum()
    summary["meta"]["real_avg_goals_per_game"] = float(real_goals / len(matches))

    with open(args.out, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Saved summary to {args.out}", file=sys.stderr)

    # Quick console readout for the test run
    print("\nTop 5 by title odds:", file=sys.stderr)
    for row in summary["per_team"][:5]:
        print(f"  {row['team']:<20} title odds {row['title_odds']*100:5.1f}%   "
              f"avg pos {row['avg_position']:.1f}   real pos {row['real_position']}", file=sys.stderr)
    print(f"\nSame champion as reality: {summary['same_champion_odds']*100:.1f}% of sims", file=sys.stderr)
    print(f"Upset ('minnow') titles: {summary['upset_titles']['probability']*100:.2f}% of sims", file=sys.stderr)
    print(f"Thrillers (>= {args.thriller_threshold} goals): {summary['thrillers']['avg_per_season']:.1f} per season on average", file=sys.stderr)


if __name__ == "__main__":
    main()
