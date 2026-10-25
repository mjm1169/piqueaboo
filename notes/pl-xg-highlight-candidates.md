# Highlight candidates — streaks, extremes and records

Across the same 1,000,000-simulation universe the treemap uses (seed 20252026), for the six metrics suggested. Every sim number maps onto a real cell in the treemap, so any of these can be wired up as a card story the same way the existing ones are.

Each candidate is set against **what actually happened in 2025/26**, and against the **xG** the run was worth — so the story can be framed as over- or under-performance rather than just a big number.

## How to pick this up later

Nothing here is wired into the site yet — this is a menu. To use one, tell
Claude the metric and the club (e.g. "give Liverpool their 21-game winning
run") and it becomes a card story like the existing ones: the sim numbers
below are real cells in the treemap, so each one can be zoomed to and opened.

Regenerate this file any time with:

    cd simulations
    python explore_highlight_candidates.py --shots data/shots_2025_26.csv \
        --n-sims 1000000 --out ../notes/pl-xg-highlight-candidates.md

(~4 minutes, ~1.5GB peak. `--n-sims 20000` for a fast sanity check.)

### What each club's card shows today

So a new pick doesn't repeat one that's already used.

| Club | Current story |
|---|---|
| Arsenal | Closest race into the final day |
| Manchester City | Highest-scoring golden boot (Haaland) + shock-relegation footnote |
| Manchester United | Worst-ever finish (19th) |
| Liverpool | Title decided by tiebreak |
| Chelsea | Title decided by tiebreak + coin-flip footnote |
| Bournemouth | Most unexpected golden boot (Evanilson) |
| Brighton, Brentford, Tottenham, Everton, Fulham | Largest winning margin (a plain league win) |
| Leeds | Lowest goal difference to win it |
| Newcastle United | Title decided by tiebreak |
| Nottingham Forest | Fewest title wins |
| Crystal Palace | Big individual haul (Mateta) |
| Aston Villa | High-scoring game (10-5 v Arsenal) |
| Burnley, Sunderland, West Ham, Wolves | Best-ever finish (never win it) |

The five clubs sharing "a plain league win" are the most obvious candidates
to replace with something from this file.

## Real-life 2025/26, for comparison

- Champion: **Arsenal** on 85pts, 5 defeats
- Longest winning run: **8** (Aston Villa)
- Longest unbeaten run: **18** (Bournemouth)
- Longest run without conceding: **4** (Arsenal)
- Fewest defeats: **5** (Arsenal)
- Longest run of games scoring: **6** (Dominic Calvert-Lewin)

## 1. Longest winning streak — 27 games

**Sim #833,296** · Arsenal — 100pts, 32W/4D/2L, GD +66
*Arsenal's season xG 79.0 for / 34.5 against (xGD +44.5)*

Arsenal win 27 in a row (real-life best that season: 8).

| # | Opponent | H/A | Score | xG |
|---|---|---|---|---|
| 1 | Newcastle United | A | 1-0 | 2.07-0.74 |
| 2 | West Ham | H | 3-2 | 3.12-0.86 |
| 3 | Fulham | A | 3-1 | 2.13-0.50 |
| 4 | Crystal Palace | H | 1-0 | 0.88-0.35 |
| 5 | Burnley | A | 2-0 | 2.52-0.68 |
| 6 | Sunderland | A | 3-0 | 2.59-1.20 |
| 7 | Tottenham | H | 3-0 | 2.28-0.03 |
| 8 | Chelsea | A | 2-1 | 1.23-0.79 |
| 9 | Brentford | H | 3-1 | 2.69-0.59 |
| 10 | Aston Villa | A | 4-0 | 1.86-3.13 |
| 11 | Wolverhampton Wanderers | H | 3-2 | 1.62-0.62 |
| 12 | Everton | A | 5-1 | 1.88-0.21 |
| 13 | Brighton | H | 3-0 | 2.85-0.73 |
| 14 | Aston Villa | H | 5-4 | 4.44-3.60 |
| 15 | Bournemouth | A | 2-0 | 1.32-0.95 |
| 16 | Liverpool | H | 1-0 | 0.70-0.32 |
| 17 | Nottingham Forest | A | 5-0 | 2.88-0.32 |
| 18 | Manchester United | H | 2-1 | 1.42-0.64 |
| 19 | Leeds | A | 5-1 | 3.55-0.18 |
| 20 | Sunderland | H | 3-1 | 1.19-0.43 |
| 21 | Brentford | A | 2-1 | 0.78-1.81 |
| 22 | Wolverhampton Wanderers | A | 1-0 | 2.03-0.17 |
| 23 | Tottenham | A | 3-1 | 3.32-0.38 |
| 24 | Chelsea | H | 2-1 | 1.72-1.35 |
| 25 | Brighton | A | 1-0 | 0.51-0.92 |
| 26 | Everton | H | 2-1 | 1.91-1.19 |
| 27 | Bournemouth | H | 2-0 | 3.16-1.40 |
| | **Total** | | **72-19** | **56.67-24.11** |

*Across the run: scored 72 from 56.67 xG (+15.33), conceded 19 from 24.11 xG (-5.11).*

## 6. Longest run without conceding — 15 games

**Sim #794** · Arsenal — 89pts, 27W/8D/3L, GD +57
*Arsenal's season xG 79.0 for / 34.5 against (xGD +44.5)*

Arsenal keep 15 clean sheets in a row (real-life best: 4).

| # | Opponent | H/A | Score | xG |
|---|---|---|---|---|
| 1 | Nottingham Forest | H | 4-0 | 2.88-0.29 |
| 2 | Manchester City | H | 2-0 | 0.72-1.12 |
| 3 | Newcastle United | A | 3-0 | 2.07-0.74 |
| 4 | West Ham | H | 5-0 | 3.12-0.86 |
| 5 | Fulham | A | 1-0 | 2.13-0.50 |
| 6 | Crystal Palace | H | 0-0 | 0.88-0.35 |
| 7 | Burnley | A | 2-0 | 2.52-0.68 |
| 8 | Sunderland | A | 2-0 | 2.59-1.20 |
| 9 | Tottenham | H | 3-0 | 2.28-0.03 |
| 10 | Chelsea | A | 1-0 | 1.23-0.79 |
| 11 | Brentford | H | 3-0 | 2.69-0.59 |
| 12 | Aston Villa | A | 3-0 | 1.86-3.13 |
| 13 | Wolverhampton Wanderers | H | 1-0 | 1.62-0.62 |
| 14 | Everton | A | 2-0 | 1.88-0.21 |
| 15 | Brighton | H | 1-0 | 2.85-0.73 |
| | **Total** | | **33-0** | **31.32-11.87** |

*Across the run: scored 33 from 31.32 xG (+1.68), conceded 0 from 11.87 xG (-11.87).*

## 6b. Longest unbeaten run — 38 games

**Sim #1,267** · Arsenal — 98pts, 30W/8D/0L, GD +58
*Arsenal's season xG 79.0 for / 34.5 against (xGD +44.5)*

Arsenal go 38 unbeaten (real-life best: 18).

| # | Opponent | H/A | Score | xG |
|---|---|---|---|---|
| 1 | Manchester United | A | 3-1 | 1.33-1.39 |
| 2 | Leeds | H | 4-0 | 2.77-0.16 |
| 3 | Liverpool | A | 0-0 | 0.49-0.48 |
| 4 | Nottingham Forest | H | 2-0 | 2.88-0.29 |
| 5 | Manchester City | H | 2-0 | 0.72-1.12 |
| 6 | Newcastle United | A | 1-1 | 2.07-0.74 |
| 7 | West Ham | H | 2-1 | 3.12-0.86 |
| 8 | Fulham | A | 2-1 | 2.13-0.50 |
| 9 | Crystal Palace | H | 2-0 | 0.88-0.35 |
| 10 | Burnley | A | 2-0 | 2.52-0.68 |
| 11 | Sunderland | A | 4-1 | 2.59-1.20 |
| 12 | Tottenham | H | 1-0 | 2.28-0.03 |
| 13 | Chelsea | A | 1-0 | 1.23-0.79 |
| 14 | Brentford | H | 2-1 | 2.69-0.59 |
| 15 | Aston Villa | A | 3-3 | 1.86-3.13 |
| 16 | Wolverhampton Wanderers | H | 1-0 | 1.62-0.62 |
| 17 | Everton | A | 1-0 | 1.88-0.21 |
| 18 | Brighton | H | 1-0 | 2.85-0.73 |
| 19 | Aston Villa | H | 5-3 | 4.44-3.60 |
| 20 | Bournemouth | A | 0-0 | 1.32-0.95 |
| 21 | Liverpool | H | 2-0 | 0.70-0.32 |
| 22 | Nottingham Forest | A | 4-0 | 2.88-0.32 |
| 23 | Manchester United | H | 3-1 | 1.42-0.64 |
| 24 | Leeds | A | 5-0 | 3.55-0.18 |
| 25 | Sunderland | H | 1-1 | 1.19-0.43 |
| 26 | Brentford | A | 1-1 | 0.78-1.81 |
| 27 | Wolverhampton Wanderers | A | 2-0 | 2.03-0.17 |
| 28 | Tottenham | A | 2-0 | 3.32-0.38 |
| 29 | Chelsea | H | 2-1 | 1.72-1.35 |
| 30 | Brighton | A | 0-0 | 0.51-0.92 |
| 31 | Everton | H | 2-1 | 1.91-1.19 |
| 32 | Bournemouth | H | 2-2 | 3.16-1.40 |
| 33 | Manchester City | A | 3-2 | 2.63-2.82 |
| 34 | Newcastle United | H | 2-1 | 0.64-0.87 |
| 35 | Fulham | H | 5-1 | 4.13-0.70 |
| 36 | West Ham | A | 3-1 | 1.52-1.32 |
| 37 | Burnley | H | 3-0 | 1.23-0.19 |
| 38 | Crystal Palace | A | 3-2 | 3.97-1.00 |
| | **Total** | | **84-26** | **78.98-34.46** |

*Across the run: scored 84 from 78.98 xG (+5.02), conceded 26 from 34.46 xG (-8.46).*

## 2. Fewest / most points to win the title

**Fewest — sim #157,581:** Arsenal — 64pts, 17W/13D/8L, GD +26 win it. *season xG 79.0 for / 34.5 against (xGD +44.5)*

**Most — sim #717,027:** Arsenal — 107pts, 35W/2D/1L, GD +68 win it. *season xG 79.0 for / 34.5 against (xGD +44.5)*

Real life: Arsenal won it on 85pts.

## 3. Most defeats and still win the title

**Sim #399,299:** Manchester City — 65pts, 21W/2D/15L, GD +20 win the league despite 15 defeats.
*season xG 81.2 for / 48.6 against (xGD +32.5)*

Real life: Arsenal lost 5.

## 4. Fewest losses in a campaign

**Sim #107,376:** Arsenal — 106pts, 34W/4D/0L, GD +63 — 0 defeats all season.
*season xG 79.0 for / 34.5 against (xGD +44.5)*

282 of 1,000,000 sims contain a team on 0 defeats; this is the highest-scoring of them. An unbeaten season happens in **282** sims (0.028%). Real-life fewest: 5 (Arsenal).

## 5. Longest run of games scoring — 24 games

**Thiago** (Brentford), sim #8,103 (real-life best that season: 6, Dominic Calvert-Lewin).

| # | Opponent | Goals | Match score |
|---|---|---|---|
| 1 | Manchester City | 1 | 1-2 |
| 2 | West Ham | 1 | 0-3 |
| 3 | Liverpool | 1 | 2-3 |
| 4 | Newcastle United | 1 | 2-1 |
| 5 | Brighton | 1 | 1-1 |
| 6 | Burnley | 2 | 5-1 |
| 7 | Tottenham | 2 | 3-2 |
| 8 | Bournemouth | 2 | 4-3 |
| 9 | Tottenham | 1 | 1-0 |
| 10 | Everton | 3 | 4-4 |
| 11 | Sunderland | 2 | 4-2 |
| 12 | Chelsea | 1 | 2-3 |
| 13 | Nottingham Forest | 1 | 3-3 |
| 14 | Newcastle United | 1 | 4-2 |
| 15 | Arsenal | 2 | 2-0 |
| 16 | Brighton | 1 | 3-2 |
| 17 | Burnley | 1 | 3-3 |
| 18 | Wolverhampton Wanderers | 2 | 2-3 |
| 19 | Leeds | 1 | 1-1 |
| 20 | Everton | 1 | 1-2 |
| 21 | Fulham | 1 | 2-0 |
| 22 | West Ham | 1 | 1-0 |
| 23 | Manchester City | 1 | 3-1 |
| 24 | Crystal Palace | 1 | 1-1 |

*Caveat worth knowing: a "game" here means a match the player took at least one shot in — the shot data can't see appearances where they didn't shoot, so a streak is never broken by a quiet game with no attempt.*

## Per-club bests — a menu, to avoid the same crest everywhere

Nearly every outright record above belongs to the same one or two clubs. These are each club's own best, so a different record can be given to a different card.

| Club | Best winning run | Best run w/o conceding | Longest unbeaten | Fewest defeats | Best title (pts) |
|---|---|---|---|---|---|
| Arsenal | 27 (sim #833,296) | 15 (sim #794) | 38 (sim #1,267) | 0 (sim #1,267) | 107 (sim #717,027) |
| Aston Villa | 17 (sim #633,427) | 9 (sim #168,107) | 32 (sim #158,017) | 3 (sim #768,138) | 87 (sim #768,138) |
| Bournemouth | 16 (sim #399,946) | 9 (sim #420,015) | 31 (sim #892,232) | 2 (sim #83,954) | 92 (sim #586,263) |
| Brentford | 14 (sim #683,279) | 10 (sim #95,102) | 26 (sim #444,763) | 3 (sim #357,749) | 91 (sim #643,033) |
| Brighton | 15 (sim #430,815) | 12 (sim #435,483) | 25 (sim #293,244) | 2 (sim #730,682) | 87 (sim #612,193) |
| Burnley | 8 (sim #552,065) | 6 (sim #531,676) | 15 (sim #490,285) | 12 (sim #804,685) | never wins it |
| Chelsea | 17 (sim #467,009) | 9 (sim #339,014) | 33 (sim #816,145) | 2 (sim #804,635) | 90 (sim #705,551) |
| Crystal Palace | 15 (sim #185,308) | 9 (sim #332,059) | 28 (sim #669,415) | 3 (sim #67,642) | 85 (sim #559,001) |
| Everton | 13 (sim #75,024) | 9 (sim #481,194) | 23 (sim #545,520) | 5 (sim #488,125) | 77 (sim #134,482) |
| Fulham | 12 (sim #276,057) | 9 (sim #912,004) | 23 (sim #634,365) | 5 (sim #68,228) | 77 (sim #687,331) |
| Leeds | 13 (sim #602,128) | 11 (sim #225,012) | 25 (sim #276,732) | 4 (sim #104,776) | 86 (sim #113,600) |
| Liverpool | 21 (sim #440,348) | 12 (sim #967,280) | 31 (sim #368,403) | 2 (sim #369,253) | 93 (sim #664,725) |
| Manchester City | 21 (sim #830,304) | 11 (sim #487,847) | 38 (sim #25,342) | 0 (sim #25,342) | 102 (sim #343,464) |
| Manchester United | 19 (sim #313,992) | 12 (sim #781,956) | 34 (sim #288,727) | 1 (sim #17,098) | 100 (sim #236,228) |
| Newcastle United | 15 (sim #196,850) | 10 (sim #47,088) | 27 (sim #358,286) | 3 (sim #358,286) | 86 (sim #975,618) |
| Nottingham Forest | 11 (sim #650,597) | 10 (sim #151,321) | 19 (sim #407,248) | 6 (sim #482,986) | 70 (sim #753,793) |
| Sunderland | 11 (sim #88,651) | 10 (sim #300,817) | 18 (sim #56,819) | 6 (sim #62,860) | never wins it |
| Tottenham | 12 (sim #928,495) | 10 (sim #883,518) | 20 (sim #322,330) | 4 (sim #272,808) | 81 (sim #561,440) |
| West Ham | 12 (sim #929,045) | 9 (sim #249,799) | 19 (sim #35,721) | 6 (sim #35,721) | never wins it |
| Wolverhampton Wanderers | 9 (sim #510,843) | 9 (sim #137,118) | 18 (sim #485,845) | 9 (sim #485,845) | never wins it |

### Longest run of games scoring, by player

| Player | Club | Longest run | Sim |
|---|---|---|---|
| Thiago | Brentford | 24 | #8,103 |
| Erling Haaland | Manchester City | 22 | #119,382 |
| Dominic Calvert-Lewin | Leeds | 21 | #708,437 |
| Ollie Watkins | Aston Villa | 16 | #138,486 |
| Hugo Ekitike | Liverpool | 14 | #34,371 |
| Jean-Philippe Mateta | Crystal Palace | 14 | #706,551 |
| João Pedro | Chelsea | 14 | #368,326 |
| Mohamed Salah | Liverpool | 14 | #728,554 |
| Thierno Barry | Everton | 14 | #168,070 |
| Benjamin Sesko | Manchester United | 13 | #296,708 |
| Beto | Everton | 13 | #67,399 |
| Evanilson | Bournemouth | 13 | #40,871 |
| Morgan Gibbs-White | Nottingham Forest | 13 | #561,319 |
| Tomas Soucek | West Ham | 13 | #249,945 |
| Bryan Mbeumo | Manchester United | 12 | #118,052 |

## Notes on method

- Champion is taken on points, then goal difference, then goals scored. A title-level tie (37 sims in the million) would be resolved on head-to-head when wired up, as the existing stories are.
- Player streaks tracked for the 255 players with at least 10 shot-games. The record found (24) is longer than that bound, so no untracked player could have beaten it.
- Team xG for/against is a property of the real shot list, identical in every simulation — it's what makes a run read as lucky or deserved.
