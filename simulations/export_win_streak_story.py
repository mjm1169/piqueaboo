"""
Exports one simulated season as a story record for a "longest winning
streak" roster-card highlight: the full final table plus the team's own
38-game campaign, in the same shape as champion-margin-stories.json /
best-seasons.json so the story modal renders it through the existing
champion-shaped code path.

Regenerates the sim bit-for-bit through the big pass's own per-match RNG
(_match_rng(seed, match_index) at the full (n_sims, ...) shape -- a
truncated shape would desync the second draw's stream position and
silently produce a different season; see build_campaign_for_sim in
export_treemap_data.py). Sim numbers therefore map onto the same
simulation as champions.bin and the treemap.

The campaign is in DATE order (the real fixture list), which is what makes
"27 wins in a row" readable as a run; the longest winning run is computed
over it and stored on the record.

Usage:
    python export_win_streak_story.py --shots data/shots_2025_26.csv \
        --sim 833296 --team Arsenal \
        --out ../articles/pl-treemap-data/win-streak-story.json
"""

import argparse
import json
import sys

import numpy as np

from simulate_season import build_match_index, build_real_table, load_shots

BIG_PASS_SEED = 20252026
BIG_PASS_N_SIMS = 1_000_000


def _match_rng(seed, match_index):
    return np.random.default_rng(np.random.SeedSequence([seed, match_index]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", required=True)
    ap.add_argument("--sim", type=int, required=True)
    ap.add_argument("--team", required=True)
    ap.add_argument("--seed", type=int, default=BIG_PASS_SEED)
    ap.add_argument("--n-sims", type=int, default=BIG_PASS_N_SIMS)
    ap.add_argument("--champions-bin", default="../articles/pl-treemap-data/champions.bin")
    ap.add_argument("--teams-json", default="../articles/pl-treemap-data/treemap-data.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    shots = load_shots(args.shots)
    matches = build_match_index(shots)
    teams = sorted(set(shots["h_team"]) | set(shots["a_team"]))
    real_table = build_real_table(shots)
    real_pos = {r["team"]: int(r["position"]) for _, r in real_table.iterrows()}

    tab = {t: dict(points=0, gf=0, ga=0, w=0, d=0, l=0) for t in teams}
    campaign = []
    for i, m in enumerate(matches):
        rng_i = _match_rng(args.seed, i)
        xh, xa = m["xg_h"], m["xg_a"]
        dh = rng_i.random((args.n_sims, len(xh))) < xh if len(xh) else np.zeros((args.n_sims, 0), dtype=bool)
        da = rng_i.random((args.n_sims, len(xa))) < xa if len(xa) else np.zeros((args.n_sims, 0), dtype=bool)
        hg, ag = int(dh[args.sim].sum()), int(da[args.sim].sum())
        for t, f, a in ((m["home_team"], hg, ag), (m["away_team"], ag, hg)):
            r = tab[t]
            r["gf"] += f; r["ga"] += a
            if f > a:
                r["points"] += 3; r["w"] += 1
            elif f == a:
                r["points"] += 1; r["d"] += 1
            else:
                r["l"] += 1
        for home in (True, False):
            t = m["home_team"] if home else m["away_team"]
            if t != args.team:
                continue
            campaign.append({
                "opponent": m["away_team"] if home else m["home_team"],
                "home": home, "date": str(m["date"]),
                "sim_goals_for": hg if home else ag,
                "sim_goals_against": ag if home else hg,
                "xg_for": round(float(xh.sum() if home else xa.sum()), 2),
                "xg_against": round(float(xa.sum() if home else xh.sum()), 2),
            })
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(matches)} matches", file=sys.stderr)

    campaign.sort(key=lambda e: e["date"])
    assert len(campaign) == 38

    rows = sorted(teams, key=lambda t: (-tab[t]["points"], -(tab[t]["gf"] - tab[t]["ga"]), -tab[t]["gf"]))
    keys = [(tab[t]["points"], tab[t]["gf"] - tab[t]["ga"], tab[t]["gf"]) for t in rows]
    assert len(set(keys)) == len(keys), "tie on points/GD/GF somewhere in the table -- needs the real tie-break chain"
    final_table = []
    for pos, t in enumerate(rows, 1):
        r = tab[t]
        final_table.append({"team": t, "position": pos, "points": r["points"], "gf": r["gf"],
                            "ga": r["ga"], "gd": r["gf"] - r["ga"], "w": r["w"], "d": r["d"], "l": r["l"]})

    champion = rows[0]
    # Longest winning run over the date-ordered campaign.
    best = cur = start = best_start = 0
    for k, e in enumerate(campaign):
        if e["sim_goals_for"] > e["sim_goals_against"]:
            if cur == 0:
                start = k
            cur += 1
            if cur > best:
                best, best_start = cur, start
        else:
            cur = 0

    # The cell this story points at is whichever team's grid the sim sits in.
    data = json.load(open(args.teams_json))
    by_byte = {t["champion_byte"]: t["team"] for t in data["teams"]}
    cell_team = by_byte[open(args.champions_bin, "rb").read()[args.sim]]
    assert cell_team == champion, f"champions.bin says {cell_team}, regeneration says {champion}"

    rec = {
        "kind": "longest_win_streak", "team": args.team, "sim": args.sim,
        "champion": champion, "champion_real_position": real_pos[champion],
        "streak_length": best, "streak_start": best_start,
        "final_table": final_table, "campaign": campaign,
    }
    with open(args.out, "w") as f:
        json.dump(rec, f, indent=1)
    row = next(r for r in final_table if r["team"] == args.team)
    print(f"sim #{args.sim:,}: {args.team} {row['points']}pts {row['w']}W/{row['d']}D/{row['l']}L "
          f"GD {row['gd']:+d}, position {row['position']}, champion {champion}; "
          f"longest winning run {best} (games {best_start+1}-{best_start+best})", file=sys.stderr)


if __name__ == "__main__":
    main()
