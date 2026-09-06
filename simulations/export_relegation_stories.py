"""
Small targeted export: real relegation-zone instances for specific real
top-6 finishers, picked by the user off
notes/pl-xg-relegated-top-team-candidates.md (itself produced by
check_relegated_top_teams.py). That note only ever wrote markdown for
picking from -- this writes the actual JSON record(s) the site fetches,
same full_table/campaign shape as best-seasons.json /
champion-margin-stories.json, so the frontend can render them through the
same existing modal code path.

Two picks, both reusing run_table_metrics_sweep() unchanged (bit-identical
regeneration via the same per-match seeding everything else in this
pipeline relies on -- no new sweep):

  - Manchester United's own single worst-ever simulated finish (their
    "lead" roster-card story, replacing the tiebreak-vs-Arsenal pick) --
    the sim where their table position is at its real historical worst
    (19th) across the full 1,000,000, tie-broken towards the lowest
    points total among ties, same "most dramatic, not a photo finish"
    convention check_relegated_top_teams.py already used for its own
    "dramatic collapse" examples.
  - Manchester City's one and only relegation instance across the whole
    million (18th, sim #445,758) -- a footnote on the Haaland golden-boot
    story, not a roster-card story of its own.

Usage:
    python export_relegation_stories.py --shots data/shots_2025_26.csv \
        --sims 1000000 --seed 20252026
"""

import argparse
import json
import sys
import time

import numpy as np

from export_treemap_data import (
    build_campaign_for_sim,
    build_final_table,
    identify_final_matchday_indices,
    run_table_metrics_sweep,
    static_match_xg,
)
from simulate_season import build_match_index, build_real_table, load_shots

# Fixed editorial picks -- see notes/pl-xg-relegated-top-team-candidates.md.
# Not derived: exactly these two teams, for exactly these reasons.
WORST_FINISH_TEAMS = ["Manchester United"]
RELEGATION_FOOTNOTE_TEAMS = ["Manchester City"]


def main():
    parser = argparse.ArgumentParser(description="Export specific top-6 relegation-zone sims as story records")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--sims", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=20252026)
    parser.add_argument("--champions-bin", default="../articles/pl-treemap-data/champions.bin")
    parser.add_argument("--out", default="../articles/pl-treemap-data/relegation-stories.json")
    args = parser.parse_args()

    shots = load_shots(args.shots)
    real_table = build_real_table(shots)
    teams = sorted(real_table["team"].tolist())
    matches = build_match_index(shots)

    final_day_indices, final_date = identify_final_matchday_indices(matches, len(teams))
    print(f"Final matchday: {final_date} ({len(final_day_indices)} matches)", file=sys.stderr)

    t0 = time.time()
    tm = run_table_metrics_sweep(matches, teams, args.sims, args.seed, final_day_indices)
    print(f"Table-metrics sweep done in {time.time()-t0:.1f}s", file=sys.stderr)

    points, gf, gd = tm["points"], tm["gf"], tm["gd"]
    n_sims, n_teams = points.shape
    # Same simplified rank key as check_relegated_top_teams.py (points, then
    # GD, then GF -- not the real head-to-head chain, since that only
    # matters for actually-tied title/relegation *deciders*, not for
    # picking a representative worst-finish/relegation instance to feature).
    rank_key = points.astype(np.int64) * 10_000_000 + (gd.astype(np.int64) + 500) * 10_000 + gf.astype(np.int64)
    order = np.argsort(-rank_key, axis=1)
    position = np.argsort(order, axis=1) + 1  # (n_sims, n_teams), 1-indexed

    champion_idx = np.fromfile(args.champions_bin, dtype=np.uint8).astype(np.int64)
    static_xg = static_match_xg(matches)

    def champion_of(sim):
        return teams[int(champion_idx[sim])]

    def build_record(team, sim, kind):
        ti = teams.index(team)
        pos = int(position[sim, ti])
        final_table = build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"],
                                         position, sim, teams)
        campaign = build_campaign_for_sim(matches, args.seed, sim, team, static_xg, args.sims)
        return {
            "kind": kind, "team": team, "sim": sim, "position": pos,
            "points": int(points[sim, ti]), "champion": champion_of(sim),
            "final_table": final_table, "campaign": campaign,
        }

    records = []

    for team in WORST_FINISH_TEAMS:
        ti = teams.index(team)
        pos_col = position[:, ti]
        worst = int(pos_col.max())
        worst_mask = pos_col == worst
        # Tie-break towards the lowest points total among sims sharing the
        # worst position -- the clearest, most dramatic instance of it,
        # not a last-day photo finish that just happened to land there.
        candidates = np.flatnonzero(worst_mask)
        sim = int(candidates[np.argmin(points[candidates, ti])])
        rec = build_record(team, sim, "worst_finish")
        print(f"{team}: worst finish {rec['position']}th on {rec['points']} points, "
              f"sim #{sim:,}, {rec['champion']} won that replay", file=sys.stderr)
        records.append(rec)

    for team in RELEGATION_FOOTNOTE_TEAMS:
        ti = teams.index(team)
        pos_col = position[:, ti]
        relegation_floor = n_teams - 3 + 1  # bottom 3, matching check_relegated_top_teams.py's default
        relegated = np.flatnonzero(pos_col >= relegation_floor)
        if relegated.size == 0:
            print(f"{team}: never relegated across {n_sims:,} sims -- skipping footnote record", file=sys.stderr)
            continue
        # Lowest points among relegated instances, same convention as above
        # (there's only one instance for Manchester City on the current
        # data, so this is moot for them specifically, but keeps the pick
        # well-defined if this list ever grows).
        sim = int(relegated[np.argmin(points[relegated, ti])])
        rec = build_record(team, sim, "relegation_footnote")
        rec["n_relegated"] = int(relegated.size)
        rec["n_sims"] = n_sims
        print(f"{team}: relegated {rec['position']}th on {rec['points']} points ({relegated.size:,} of "
              f"{n_sims:,} sims), sim #{sim:,}, {rec['champion']} won that replay", file=sys.stderr)
        records.append(rec)

    with open(args.out, "w") as f:
        json.dump(records, f)
    print(f"Wrote {len(records)} record(s) to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
