"""
One-off check: across the same 1,000,000-sim universe champions.bin comes
from, how often does one of this season's real top-6 finishers end up
relegated (bottom 3) instead? Answers the user's "check if any top teams
end up getting relegated" ask before committing to a new curated-tour
stop or roster-card story -- this only reports counts/examples, it
doesn't write any new output file or touch the site.

Reuses run_table_metrics_sweep() unchanged (regenerates every match's
draws bit-identically via the same per-match seeding everything else in
this pipeline relies on) rather than a bespoke pass, since the position
array it already computes for every sim/team is exactly what this needs.

Usage:
    python check_relegated_top_teams.py --shots data/shots_2025_26.csv \
        --sims 1000000 --seed 20252026
"""

import argparse
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


def main():
    parser = argparse.ArgumentParser(description="Check how often real top-6 teams get relegated in the sims")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--sims", type=int, default=1_000_000)
    parser.add_argument("--seed", type=int, default=20252026)
    parser.add_argument("--top-n", type=int, default=6, help="How many real-table places count as 'top'")
    parser.add_argument("--bottom-n", type=int, default=3, help="How many table places count as 'relegated'")
    parser.add_argument("--champions-bin", default="../articles/pl-treemap-data/champions.bin",
                         help="Existing champions.bin, for the example sims' own champion name")
    parser.add_argument("--notes-out", default="../notes/pl-xg-relegated-top-team-candidates.md",
                         help="Where to write the candidates note (full final tables + campaign summaries "
                              "for each example sim found)")
    args = parser.parse_args()

    shots = load_shots(args.shots)
    real_table = build_real_table(shots)
    teams = sorted(real_table["team"].tolist())
    matches = build_match_index(shots)
    real_pos = {row["team"]: int(row["position"]) for _, row in real_table.iterrows()}

    top_teams = [t for t, p in real_pos.items() if p <= args.top_n]
    top_teams.sort(key=lambda t: real_pos[t])
    print(f"Real top {args.top_n}: " + ", ".join(f"{t} ({real_pos[t]})" for t in top_teams), file=sys.stderr)

    final_day_indices, final_date = identify_final_matchday_indices(matches, len(teams))
    print(f"Final matchday: {final_date} ({len(final_day_indices)} matches)", file=sys.stderr)

    t0 = time.time()
    tm = run_table_metrics_sweep(matches, teams, args.sims, args.seed, final_day_indices)
    print(f"Table-metrics sweep done in {time.time()-t0:.1f}s", file=sys.stderr)

    points, gf, gd = tm["points"], tm["gf"], tm["gd"]
    n_sims, n_teams = points.shape
    rank_key = points.astype(np.int64) * 10_000_000 + (gd.astype(np.int64) + 500) * 10_000 + gf.astype(np.int64)
    order = np.argsort(-rank_key, axis=1)
    position = np.argsort(order, axis=1) + 1  # (n_sims, n_teams), 1-indexed

    relegation_floor = n_teams - args.bottom_n + 1  # e.g. 18 for bottom 3 of 20

    print()
    print(f"{'Team':<24}{'Real pos':>9}{'Worst sim pos':>15}{'# sims relegated':>18}{'% of sims':>11}")
    results = []
    for team in top_teams:
        ti = teams.index(team)
        pos_col = position[:, ti]
        worst = int(pos_col.max())
        relegated_mask = pos_col >= relegation_floor
        n_relegated = int(relegated_mask.sum())
        pct = 100.0 * n_relegated / n_sims
        print(f"{team:<24}{real_pos[team]:>9}{worst:>15}{n_relegated:>18,}{pct:>10.3f}%")
        if n_relegated:
            relegated_sims = np.flatnonzero(relegated_mask)
            # Two examples per team, for variety: the most dramatic
            # collapse (worst points total among that team's own
            # relegated sims -- clearly relegated, not a last-day photo
            # finish) and the narrowest brush with it (highest points
            # total that still finishes in the bottom bottom_n -- "how
            # close does a genuinely good points tally still come to
            # going down").
            worst_idx = int(relegated_sims[np.argmin(points[relegated_sims, ti])])
            narrow_idx = int(relegated_sims[np.argmax(points[relegated_sims, ti])])
            results.append({
                "team": team, "real_position": real_pos[team], "worst_position": worst,
                "n_relegated": n_relegated, "pct": pct,
                "dramatic_sim": worst_idx, "dramatic_position": int(pos_col[worst_idx]),
                "dramatic_points": int(points[worst_idx, ti]),
                "narrow_sim": narrow_idx, "narrow_position": int(pos_col[narrow_idx]),
                "narrow_points": int(points[narrow_idx, ti]),
            })

    print()
    if not results:
        print(f"No real top-{args.top_n} team ever finishes in the bottom {args.bottom_n} "
              f"across all {n_sims:,} sims.")
        return

    print(f"{len(results)} of the real top {args.top_n} get relegated at least once. Building full "
          f"detail for the candidates note...", file=sys.stderr)

    champion_idx = np.fromfile(args.champions_bin, dtype=np.uint8).astype(np.int64)
    static_xg = static_match_xg(matches)

    def champion_of(sim):
        return teams[int(champion_idx[sim])]

    def build_detail(sim, team):
        final_table = build_final_table(tm["points"], tm["gf"], tm["ga"], tm["wins"], tm["draws"], tm["losses"],
                                         position, sim, teams)
        campaign = build_campaign_for_sim(matches, args.seed, sim, team, static_xg, args.sims)
        return final_table, campaign

    lines = [
        "# Relegated top-team candidates",
        "",
        f"You asked whether any of this season's real top {args.top_n} finishers ever get "
        f"relegated in the 1,000,000 sims. {len(results)} of them do -- table below, plus two "
        "example sims per team (a dramatic collapse and a narrower brush with it) with the full "
        "final table and that team's own 38-game campaign log for each, so you can pick which "
        "one(s) (if any) to feature. Real, drawn straight from the simulation output -- nothing "
        "here is invented.",
        "",
        f"| Team | Real position | Worst sim finish | Times relegated | % of sims |",
        f"|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['team']} | {r['real_position']} | {r['worst_position']}th | "
                      f"{r['n_relegated']:,} | {r['pct']:.3f}% |")
    lines.append("")

    for r in results:
        team = r["team"]
        lines.append(f"## {team} (real {r['real_position']})")
        lines.append("")
        for label, sim, pos, pts in (
            ("Dramatic collapse", r["dramatic_sim"], r["dramatic_position"], r["dramatic_points"]),
            ("Narrow brush with it", r["narrow_sim"], r["narrow_position"], r["narrow_points"]),
        ):
            champ = champion_of(sim)
            lines.append(f"### {label} -- sim #{sim:,}")
            lines.append("")
            lines.append(f"{team} finish {pos}th on {pts} points; {champ} win the league this time.")
            lines.append("")
            final_table, campaign = build_detail(sim, team)
            lines.append("**Final table:**")
            lines.append("")
            lines.append("| Pos | Team | Pts | GD | W | D | L |")
            lines.append("|---|---|---|---|---|---|---|")
            for row in final_table:
                marker = f"**{row['team']}**" if row["team"] == team else row["team"]
                lines.append(f"| {row['position']} | {marker} | {row['points']} | {row['gd']:+d} | "
                              f"{row['w']} | {row['d']} | {row['l']} |")
            lines.append("")
            wins = sum(1 for g in campaign if g["sim_goals_for"] > g["sim_goals_against"])
            draws_ = sum(1 for g in campaign if g["sim_goals_for"] == g["sim_goals_against"])
            losses = len(campaign) - wins - draws_
            lines.append(f"{team}'s campaign: {wins}W {draws_}D {losses}L, "
                         f"{sum(g['sim_goals_for'] for g in campaign)} scored, "
                         f"{sum(g['sim_goals_against'] for g in campaign)} conceded.")
            lines.append("")

    with open(args.notes_out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote candidates note to {args.notes_out}", file=sys.stderr)


if __name__ == "__main__":
    main()
