"""
Explores candidate "highlight" stories across the big pass's own
1,000,000-sim universe, for metrics the existing curated tour /
roster-card stories don't already cover:

  1. longest winning streak by a team
  2. fewest / most points to win the title
  3. most defeats and still win the title
  4. fewest (ideally zero) losses in a campaign
  5. longest run of games scoring, for a player
  6. longest run of games without conceding, for a team

Every candidate is reported alongside its xG context -- what the run was
"worth" on chances versus what it actually returned -- plus the real
2025/26 equivalent, so a pick can be framed as over- or under-performance
rather than just a number.

Read-only: writes a notes file, changes nothing the site reads. Uses the
same per-match RNG scheme as every other script here
(_match_rng(seed, match_index), full (n_sims, ...) shape) so every sim
number quoted maps onto the same simulation as champions.bin and the
treemap -- see export_treemap_data.py's build_campaign_for_sim docstring
for why a truncated shape would silently regenerate a different season.

Usage:
    python explore_highlight_candidates.py --shots data/shots_2025_26.csv \
        --n-sims 1000000 --out ../notes/pl-xg-highlight-candidates.md
"""

import argparse
import sys
import time

import numpy as np

from simulate_season import build_match_index, load_shots

BIG_PASS_SEED = 20252026
BIG_PASS_N_SIMS = 1_000_000

# A player's scoring streak can't be longer than the number of matches
# they take a shot in, so players below this bound are not tracked. The
# run asserts the record found is >= this, which proves no untracked
# player could have beaten it.
MIN_SHOT_GAMES = 10


def _match_rng(seed, match_index):
    return np.random.default_rng(np.random.SeedSequence([seed, match_index]))


def run_sweep(matches, teams, n_sims, seed, tracked_players):
    """One date-ordered pass over all 380 matches, vectorised across sims."""
    n_teams = len(teams)
    team_idx = {t: i for i, t in enumerate(teams)}

    pts = np.zeros((n_sims, n_teams), dtype=np.int16)
    gf = np.zeros((n_sims, n_teams), dtype=np.int16)
    ga = np.zeros((n_sims, n_teams), dtype=np.int16)
    wins = np.zeros((n_sims, n_teams), dtype=np.int16)
    draws_n = np.zeros((n_sims, n_teams), dtype=np.int16)
    losses = np.zeros((n_sims, n_teams), dtype=np.int16)

    win_cur = np.zeros((n_sims, n_teams), dtype=np.int8)
    win_max = np.zeros((n_sims, n_teams), dtype=np.int8)
    unb_cur = np.zeros((n_sims, n_teams), dtype=np.int8)
    unb_max = np.zeros((n_sims, n_teams), dtype=np.int8)
    cs_cur = np.zeros((n_sims, n_teams), dtype=np.int8)
    cs_max = np.zeros((n_sims, n_teams), dtype=np.int8)

    # per-player scoring-streak state, for the tracked subset only
    p_cur = {p: np.zeros(n_sims, dtype=np.int8) for p in tracked_players}
    p_max = {p: np.zeros(n_sims, dtype=np.int8) for p in tracked_players}

    t0 = time.time()
    for mi, m in enumerate(matches):
        h, a = team_idx[m["home_team"]], team_idx[m["away_team"]]
        xg_h, xg_a = m["xg_h"], m["xg_a"]
        rng_i = _match_rng(seed, mi)
        dh = rng_i.random((n_sims, len(xg_h))) < xg_h if len(xg_h) else np.zeros((n_sims, 0), dtype=bool)
        da = rng_i.random((n_sims, len(xg_a))) < xg_a if len(xg_a) else np.zeros((n_sims, 0), dtype=bool)

        hg = dh.sum(axis=1).astype(np.int16)
        ag = da.sum(axis=1).astype(np.int16)
        h_win, a_win = hg > ag, ag > hg
        drawn = hg == ag

        pts[:, h] += np.where(h_win, 3, np.where(drawn, 1, 0)).astype(np.int16)
        pts[:, a] += np.where(a_win, 3, np.where(drawn, 1, 0)).astype(np.int16)
        gf[:, h] += hg; ga[:, h] += ag
        gf[:, a] += ag; ga[:, a] += hg
        wins[:, h] += h_win; wins[:, a] += a_win
        draws_n[:, h] += drawn; draws_n[:, a] += drawn
        losses[:, h] += a_win; losses[:, a] += h_win

        for side, won, unbeaten, conceded in ((h, h_win, ~a_win, ag > 0),
                                              (a, a_win, ~h_win, hg > 0)):
            win_cur[:, side] = np.where(won, win_cur[:, side] + 1, 0)
            np.maximum(win_max[:, side], win_cur[:, side], out=win_max[:, side])
            unb_cur[:, side] = np.where(unbeaten, unb_cur[:, side] + 1, 0)
            np.maximum(unb_max[:, side], unb_cur[:, side], out=unb_max[:, side])
            cs_cur[:, side] = np.where(~conceded, cs_cur[:, side] + 1, 0)
            np.maximum(cs_max[:, side], cs_cur[:, side], out=cs_max[:, side])

        for players, draws_side in ((m["players_h"], dh), (m["players_a"], da)):
            for p in np.unique(players):
                if p not in p_cur:
                    continue
                cols = np.flatnonzero(players == p)
                scored = draws_side[:, cols].any(axis=1)
                cur = p_cur[p]
                np.add(cur, 1, out=cur, where=scored)
                cur[~scored] = 0
                np.maximum(p_max[p], cur, out=p_max[p])

        if (mi + 1) % 50 == 0:
            print(f"  [sweep] {mi+1}/{len(matches)} matches, {time.time()-t0:.0f}s", file=sys.stderr)

    return dict(pts=pts, gf=gf, ga=ga, wins=wins, draws=draws_n, losses=losses,
                win_max=win_max, unb_max=unb_max, cs_max=cs_max,
                p_max=p_max)


def real_world_baselines(shots, teams):
    """The same six metrics, measured on what actually happened in 2025/26."""
    res = shots.drop_duplicates("match_id")[["match_id", "h_team", "a_team", "h_goals", "a_goals", "date"]]
    res = res.sort_values("date", kind="stable")
    pts = {t: 0 for t in teams}; L = {t: 0 for t in teams}
    wcur = {t: 0 for t in teams}; wmax = {t: 0 for t in teams}
    ccur = {t: 0 for t in teams}; cmax = {t: 0 for t in teams}
    ucur = {t: 0 for t in teams}; umax = {t: 0 for t in teams}
    for _, r in res.iterrows():
        for side, gfx, gax in ((r["h_team"], r["h_goals"], r["a_goals"]),
                               (r["a_team"], r["a_goals"], r["h_goals"])):
            if gfx > gax:
                pts[side] += 3; wcur[side] += 1; ucur[side] += 1
            elif gfx == gax:
                pts[side] += 1; wcur[side] = 0; ucur[side] += 1
            else:
                L[side] += 1; wcur[side] = 0; ucur[side] = 0
            ccur[side] = ccur[side] + 1 if gax == 0 else 0
            wmax[side] = max(wmax[side], wcur[side])
            cmax[side] = max(cmax[side], ccur[side])
            umax[side] = max(umax[side], ucur[side])
    champ = max(teams, key=lambda t: pts[t])
    goals = shots[shots["result"] == "Goal"]
    order = {int(r["match_id"]): k for k, (_, r) in enumerate(res.iterrows())}
    best_p, best_n = None, 0
    for player, g in shots.groupby("player"):
        seen = sorted(set(g["match_id"]), key=lambda m: order[int(m)])
        scored_in = set(goals[goals["player"] == player]["match_id"])
        cur = 0
        for m in seen:
            cur = cur + 1 if m in scored_in else 0
            if cur > best_n:
                best_n, best_p = cur, player
    return {
        "champion": champ, "champion_points": pts[champ], "champion_losses": L[champ],
        "best_win_streak": max(wmax.values()),
        "best_win_streak_team": max(teams, key=lambda t: wmax[t]),
        "best_cs_streak": max(cmax.values()),
        "best_cs_streak_team": max(teams, key=lambda t: cmax[t]),
        "best_unbeaten": max(umax.values()),
        "best_unbeaten_team": max(teams, key=lambda t: umax[t]),
        "fewest_losses": min(L.values()),
        "fewest_losses_team": min(teams, key=lambda t: L[t]),
        "best_scoring_streak": best_n, "best_scoring_streak_player": best_p,
    }


def team_season_xg(shots, teams):
    """Static per-team xG for/against -- identical in every simulation."""
    out = {t: {"xg_for": 0.0, "xg_against": 0.0} for t in teams}
    for _, r in shots.iterrows():
        att = r["h_team"] if r["h_a"] == "h" else r["a_team"]
        dfd = r["a_team"] if r["h_a"] == "h" else r["h_team"]
        out[att]["xg_for"] += float(r["xG"])
        out[dfd]["xg_against"] += float(r["xG"])
    return out


def replay_sims(matches, n_sims, seed, sim_list):
    """
    One more date-ordered pass, keeping full per-match detail for just the
    handful of candidate sims -- same full-shape draw as the sweep, so the
    detail matches those sims exactly.
    """
    sims = np.array(sorted(set(int(s) for s in sim_list)), dtype=np.int64)
    pos = {int(s): k for k, s in enumerate(sims)}
    per_match = []
    for mi, m in enumerate(matches):
        rng_i = _match_rng(seed, mi)
        dh = rng_i.random((n_sims, len(m["xg_h"]))) < m["xg_h"] if len(m["xg_h"]) else np.zeros((n_sims, 0), dtype=bool)
        da = rng_i.random((n_sims, len(m["xg_a"]))) < m["xg_a"] if len(m["xg_a"]) else np.zeros((n_sims, 0), dtype=bool)
        sub_h, sub_a = dh[sims], da[sims]
        scorers = []
        for players, sub in ((m["players_h"], sub_h), (m["players_a"], sub_a)):
            d = {}
            for p in np.unique(players):
                cols = np.flatnonzero(players == p)
                d[str(p)] = sub[:, cols].sum(axis=1)
            scorers.append(d)
        per_match.append({
            "home": m["home_team"], "away": m["away_team"],
            "hg": sub_h.sum(axis=1), "ag": sub_a.sum(axis=1),
            "xg_h": float(m["xg_h"].sum()), "xg_a": float(m["xg_a"].sum()),
            "goals_h": scorers[0], "goals_a": scorers[1],
        })
    return pos, per_match


def streak_games(per_match, slot, team, kind, length):
    """The actual run of matches behind a streak, for the report."""
    cur = []
    for pm in per_match:
        if team not in (pm["home"], pm["away"]):
            continue
        home = pm["home"] == team
        gfx = int(pm["hg"][slot]) if home else int(pm["ag"][slot])
        gax = int(pm["ag"][slot]) if home else int(pm["hg"][slot])
        xgf = pm["xg_h"] if home else pm["xg_a"]
        xga = pm["xg_a"] if home else pm["xg_h"]
        ok = (gfx > gax) if kind == "win" else (gax == 0 if kind == "cs" else gfx >= gax)
        if ok:
            cur.append({"opp": pm["away"] if home else pm["home"], "home": home,
                        "gf": gfx, "ga": gax, "xgf": xgf, "xga": xga})
            if len(cur) >= length:
                return cur[:length]
        else:
            cur = []
    return []


def player_streak_games(per_match, slot, player, length):
    cur = []
    for pm in per_match:
        for side, opp in (("goals_h", pm["away"]), ("goals_a", pm["home"])):
            if player not in pm[side]:
                continue
            g = int(pm[side][player][slot])
            if g > 0:
                cur.append({"opp": opp, "goals": g,
                            "score": str(int(pm["hg"][slot])) + "-" + str(int(pm["ag"][slot]))})
                if len(cur) >= length:
                    return cur[:length]
            else:
                cur = []
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", required=True)
    ap.add_argument("--n-sims", type=int, default=BIG_PASS_N_SIMS)
    ap.add_argument("--seed", type=int, default=BIG_PASS_SEED)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    shots = load_shots(args.shots)
    matches = build_match_index(shots)
    teams = sorted(set(shots["h_team"]) | set(shots["a_team"]))
    n_teams = len(teams)

    shot_games = shots.groupby("player")["match_id"].nunique()
    tracked = sorted(shot_games[shot_games >= MIN_SHOT_GAMES].index)
    print(f"{len(matches)} matches, {n_teams} teams, {args.n_sims:,} sims; "
          f"tracking {len(tracked)} players with >= {MIN_SHOT_GAMES} shot-games", file=sys.stderr)

    player_club = {}
    for _, r in shots.iterrows():
        player_club.setdefault(r["player"], r["h_team"] if r["h_a"] == "h" else r["a_team"])

    real = real_world_baselines(shots, teams)
    xg = team_season_xg(shots, teams)
    sw = run_sweep(matches, teams, args.n_sims, args.seed, set(tracked))

    pts, gf, ga = sw["pts"].astype(np.int32), sw["gf"].astype(np.int32), sw["ga"].astype(np.int32)
    losses, wins = sw["losses"], sw["wins"]
    gd = gf - ga
    rank_key = pts * 10_000_000 + (gd + 500) * 10_000 + gf
    champ_i = rank_key.argmax(axis=1)
    rows = np.arange(args.n_sims)
    champ_pts = pts[rows, champ_i]
    champ_losses = losses[rows, champ_i]

    def best(mat, mode="max"):
        """(sim, team_index, value) of the global max/min over a (sims, teams) array."""
        per_sim = mat.max(axis=1) if mode == "max" else mat.min(axis=1)
        sim = int(per_sim.argmax() if mode == "max" else per_sim.argmin())
        ti = int(mat[sim].argmax() if mode == "max" else mat[sim].argmin())
        return sim, ti, int(mat[sim, ti])

    win_sim, win_ti, win_len = best(sw["win_max"])
    cs_sim, cs_ti, cs_len = best(sw["cs_max"])
    unb_sim, unb_ti, unb_len = best(sw["unb_max"])
    # Fewest losses will tie across a great many sims once unbeaten
    # seasons appear at all, so pick the most impressive of them (most
    # points) rather than whichever numpy happens to reach first.
    fl_len = int(losses.min())
    fl_mask = losses == fl_len
    fl_pts = np.where(fl_mask, pts, -1)
    fl_sim = int(fl_pts.max(axis=1).argmax())
    fl_ti = int(fl_pts[fl_sim].argmax())
    n_fl = int(fl_mask.any(axis=1).sum())

    fewest_pts_sim = int(champ_pts.argmin()); most_pts_sim = int(champ_pts.argmax())
    most_def_sim = int(champ_losses.argmax())

    p_best = {p: int(sw["p_max"][p].max()) for p in tracked}
    p_name = max(p_best, key=lambda k: p_best[k])
    p_len = p_best[p_name]
    p_sim = int(sw["p_max"][p_name].argmax())
    assert p_len >= MIN_SHOT_GAMES, (
        f"record scoring streak {p_len} is below the {MIN_SHOT_GAMES}-shot-game tracking "
        "bound, so an untracked player could in principle beat it -- lower MIN_SHOT_GAMES")

    cands = [win_sim, cs_sim, unb_sim, fl_sim, fewest_pts_sim, most_pts_sim, most_def_sim, p_sim]
    print(f"replaying {len(set(cands))} candidate sims for detail...", file=sys.stderr)
    slot, per_match = replay_sims(matches, args.n_sims, args.seed, cands)

    def table_line(sim, ti):
        t = teams[ti]
        return (f"{t} — {int(pts[sim, ti])}pts, {int(wins[sim, ti])}W/"
                f"{int(sw['draws'][sim, ti])}D/{int(losses[sim, ti])}L, "
                f"GD {int(gd[sim, ti]):+d}")

    def xg_line(t):
        d = xg[t]
        return (f"season xG {d['xg_for']:.1f} for / {d['xg_against']:.1f} against "
                f"(xGD {d['xg_for'] - d['xg_against']:+.1f})")

    def run_block(games, label):
        out = [f"| # | Opponent | H/A | Score | xG |", "|---|---|---|---|---|"]
        tg = ta = txf = txa = 0
        for k, g in enumerate(games, 1):
            out.append(f"| {k} | {g['opp']} | {'H' if g['home'] else 'A'} | "
                       f"{g['gf']}-{g['ga']} | {g['xgf']:.2f}-{g['xga']:.2f} |")
            tg += g["gf"]; ta += g["ga"]; txf += g["xgf"]; txa += g["xga"]
        out.append(f"| | **Total** | | **{tg}-{ta}** | **{txf:.2f}-{txa:.2f}** |")
        out.append("")
        out.append(f"*{label}: scored {tg} from {txf:.2f} xG ({tg - txf:+.2f}), "
                   f"conceded {ta} from {txa:.2f} xG ({ta - txa:+.2f}).*")
        return "\n".join(out)

    L = []
    w = L.append
    w("# Highlight candidates — streaks, extremes and records")
    w("")
    w(f"Across the same {args.n_sims:,}-simulation universe the treemap uses "
      f"(seed {args.seed}), for the six metrics suggested. Every sim number maps "
      "onto a real cell in the treemap, so any of these can be wired up as a card "
      "story the same way the existing ones are.")
    w("")
    w("Each candidate is set against **what actually happened in 2025/26**, and "
      "against the **xG** the run was worth — so the story can be framed as "
      "over- or under-performance rather than just a big number.")
    w("")
    w("## Real-life 2025/26, for comparison")
    w("")
    w(f"- Champion: **{real['champion']}** on {real['champion_points']}pts, "
      f"{real['champion_losses']} defeats")
    w(f"- Longest winning run: **{real['best_win_streak']}** "
      f"({real['best_win_streak_team']})")
    w(f"- Longest unbeaten run: **{real['best_unbeaten']}** "
      f"({real['best_unbeaten_team']})")
    w(f"- Longest run without conceding: **{real['best_cs_streak']}** "
      f"({real['best_cs_streak_team']})")
    w(f"- Fewest defeats: **{real['fewest_losses']}** ({real['fewest_losses_team']})")
    w(f"- Longest run of games scoring: **{real['best_scoring_streak']}** "
      f"({real['best_scoring_streak_player']})")
    w("")

    def section(n, title, sim, ti, body_lines):
        w(f"## {n}. {title}")
        w("")
        w(f"**Sim #{sim:,}** · {table_line(sim, ti)}")
        w(f"*{teams[ti]}'s {xg_line(teams[ti])}*")
        w("")
        for b in body_lines:
            w(b)
        w("")

    g = streak_games(per_match, slot[win_sim], teams[win_ti], "win", win_len)
    section(1, f"Longest winning streak — {win_len} games", win_sim, win_ti, [
        f"{teams[win_ti]} win {win_len} in a row (real-life best that season: "
        f"{real['best_win_streak']}).", "", run_block(g, "Across the run")])

    g = streak_games(per_match, slot[cs_sim], teams[cs_ti], "cs", cs_len)
    section(6, f"Longest run without conceding — {cs_len} games", cs_sim, cs_ti, [
        f"{teams[cs_ti]} keep {cs_len} clean sheets in a row (real-life best: "
        f"{real['best_cs_streak']}).", "", run_block(g, "Across the run")])

    g = streak_games(per_match, slot[unb_sim], teams[unb_ti], "unb", unb_len)
    section("6b", f"Longest unbeaten run — {unb_len} games", unb_sim, unb_ti, [
        f"{teams[unb_ti]} go {unb_len} unbeaten (real-life best: {real['best_unbeaten']}).",
        "", run_block(g, "Across the run")])

    w("## 2. Fewest / most points to win the title")
    w("")
    w(f"**Fewest — sim #{fewest_pts_sim:,}:** {table_line(fewest_pts_sim, int(champ_i[fewest_pts_sim]))} "
      f"win it. *{xg_line(teams[int(champ_i[fewest_pts_sim])])}*")
    w("")
    w(f"**Most — sim #{most_pts_sim:,}:** {table_line(most_pts_sim, int(champ_i[most_pts_sim]))} "
      f"win it. *{xg_line(teams[int(champ_i[most_pts_sim])])}*")
    w("")
    w(f"Real life: {real['champion']} won it on {real['champion_points']}pts.")
    w("")

    w("## 3. Most defeats and still win the title")
    w("")
    w(f"**Sim #{most_def_sim:,}:** {table_line(most_def_sim, int(champ_i[most_def_sim]))} "
      f"win the league despite {int(champ_losses[most_def_sim])} defeats.")
    w(f"*{xg_line(teams[int(champ_i[most_def_sim])])}*")
    w("")
    w(f"Real life: {real['champion']} lost {real['champion_losses']}.")
    w("")

    unbeaten_sims = int((losses.min(axis=1) == 0).sum())
    _ = n_fl
    w("## 4. Fewest losses in a campaign")
    w("")
    w(f"**Sim #{fl_sim:,}:** {table_line(fl_sim, fl_ti)} — {fl_len} defeats all season.")
    w(f"*{xg_line(teams[fl_ti])}*")
    w("")
    w(f"{n_fl:,} of {args.n_sims:,} sims contain a team on {fl_len} defeats; this is the "
      f"highest-scoring of them. An unbeaten season happens in **{unbeaten_sims:,}** sims "
      f"({unbeaten_sims / args.n_sims * 100:.3f}%). Real-life fewest: "
      f"{real['fewest_losses']} ({real['fewest_losses_team']}).")
    w("")

    pg = player_streak_games(per_match, slot[p_sim], p_name, p_len)
    w(f"## 5. Longest run of games scoring — {p_len} games")
    w("")
    w(f"**{p_name}** ({player_club.get(p_name, '?')}), sim #{p_sim:,} (real-life best that season: "
      f"{real['best_scoring_streak']}, {real['best_scoring_streak_player']}).")
    w("")
    w("| # | Opponent | Goals | Match score |")
    w("|---|---|---|---|")
    for k, x in enumerate(pg, 1):
        w(f"| {k} | {x['opp']} | {x['goals']} | {x['score']} |")
    w("")
    w(f"*Caveat worth knowing: a \"game\" here means a match the player took at "
      f"least one shot in — the shot data can't see appearances where they didn't "
      f"shoot, so a streak is never broken by a quiet game with no attempt.*")
    w("")

    # ---- per-club menu -------------------------------------------------
    # Almost every outright record belongs to whichever club is strongest
    # on xG, so an outright-best-only list would put the same crest on
    # every card. These tables give each club its own best, which is what
    # actually lets the highlights be spread around.
    w("## Per-club bests — a menu, to avoid the same crest everywhere")
    w("")
    w("Nearly every outright record above belongs to the same one or two clubs. "
      "These are each club's own best, so a different record can be given to a "
      "different card.")
    w("")
    w("| Club | Best winning run | Best run w/o conceding | Longest unbeaten | Fewest defeats | Best title (pts) |")
    w("|---|---|---|---|---|---|")
    # Best title-winning points total, and the sim it happened in -- taken
    # among that club's CHAMPION sims only. (An earlier cut read the sim
    # off the club's highest-points season overall, which isn't
    # necessarily one they won.)
    champ_pts_by_team = {}
    for ti, t in enumerate(teams):
        idx = np.flatnonzero(champ_i == ti)
        if len(idx):
            k = idx[pts[idx, ti].argmax()]
            champ_pts_by_team[t] = (int(pts[k, ti]), int(k))
        else:
            champ_pts_by_team[t] = None
    for ti, t in enumerate(teams):
        wm = sw["win_max"][:, ti]; cm = sw["cs_max"][:, ti]; um = sw["unb_max"][:, ti]
        lm = losses[:, ti]
        bp = champ_pts_by_team[t]
        bp_txt = f"{bp[0]} (sim #{bp[1]:,})" if bp else "never wins it"
        w(f"| {t} | {int(wm.max())} (sim #{int(wm.argmax()):,}) "
          f"| {int(cm.max())} (sim #{int(cm.argmax()):,}) "
          f"| {int(um.max())} (sim #{int(um.argmax()):,}) "
          f"| {int(lm.min())} (sim #{int(lm.argmin()):,}) "
          f"| {bp_txt} |")
    w("")

    w("### Longest run of games scoring, by player")
    w("")
    w("| Player | Club | Longest run | Sim |")
    w("|---|---|---|---|")
    top = sorted(p_best.items(), key=lambda kv: -kv[1])[:15]
    for name, n in top:
        w(f"| {name} | {player_club.get(name, '?')} | {n} | #{int(sw['p_max'][name].argmax()):,} |")
    w("")

    w("## Notes on method")
    w("")
    w(f"- Champion is taken on points, then goal difference, then goals scored. "
      f"A title-level tie (37 sims in the million) would be resolved on "
      f"head-to-head when wired up, as the existing stories are.")
    w(f"- Player streaks tracked for the {len(tracked)} players with at least "
      f"{MIN_SHOT_GAMES} shot-games. The record found ({p_len}) is longer than "
      f"that bound, so no untracked player could have beaten it.")
    w(f"- Team xG for/against is a property of the real shot list, identical in "
      f"every simulation — it's what makes a run read as lucky or deserved.")
    w("")

    with open(args.out, "w") as f:
        f.write("\n".join(L))
    print(f"wrote {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
