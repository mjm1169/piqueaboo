# Roster card content: candidate ideas

You said the roster cards (the grid below the treemap, one card per club)
feel thin, and floated the idea of showing a "best season" for clubs that
never win in the 1,000,000 sims. Lower priority — for whenever you want to
pick this up.

## Status (2026-08-29)

**Done:** the 4 zero-win clubs' "best season" — you picked this option over
the two free ones below. Turned out to be cheaper than flagged at the time:
the per-sim, per-team position tracking it needs already existed as a
byproduct of the curated tour's own "no wins" stop (`derive_table_stories`'s
`no_wins` dict), just discarded after picking the single best-of-4 team for
that one tour slot. `export_treemap_data.py` now has a `build_best_seasons`
pass that keeps all 4, with each team's own full final table and 38-game
campaign log, written to `articles/pl-treemap-data/best-seasons.json`. Each
of the 4 clubs now gets a real roster card (`.roster-card.zero`, a class
that already existed in the CSS but was never wired up) with a "Best-ever
finish" button opening the same story-modal treatment the tour already
uses for this. The old one-line "never won it: A, B, C, D" summary text is
gone, replaced by the 4 individual cards.

**Still open:** which framing to use for the 16 clubs that do win — see the
table below, added so you can pick per club rather than one blanket rule.

## What a card shows today

Crest, colour swatch, name, title count/odds ("X / 1,000,000 · Y%"), and —
only for clubs that have at least one win — a row of small buttons linking
to that club's curated stories (currently drawn from the small 20,000-sim
story batch, so only ever "champion" stories). The 4 clubs that never win
(Burnley, Sunderland, West Ham, Wolves) get nothing beyond the bare stat
line — that's almost certainly what's reading as thin.

## The "best season" idea — a data note first

Worth flagging before you pick this: "best season" (best final league
position across all 1,000,000 sims) **isn't computable from what's
currently saved**. The big pass only records full-table detail for flagged
*champions* (unexpected winners) — an ordinary team's position in an
ordinary sim is discarded once that sim's points/GD/GF are folded into the
running totals, so there's no record of, say, Wolves' best-ever finish
across the million. Getting real "best season" data would mean a small
extra pass — cheap in principle (streaming again, just tracking a running
best-position per team instead of discarding it), but it is new backend
work, not a client-side change. Flagging so you can weigh it against the
options below that use data we already have.

## Candidates for the 16 clubs that do win

1. **Comparison framing.** Restate the odds against reality — "X% here vs.
   0% in reality" for a club that's never actually won it, or "X% here,
   which is Nx more/less than how often [club] actually finished top
   4/relegated/etc." Needs no new data, just a bit of arithmetic on
   `real_position`, which every team already carries.
2. **A second story slot.** Right now a club's story buttons are capped by
   whatever the 20,000-sim batch happened to produce. Pulling one of the
   flagged-game stories (high-scoring / big-haul) that happens to involve
   this club — even in a sim they didn't win — would surface more variety
   without new backend work, since `flagged-games.json` isn't filtered by
   who won the league.

## Candidates for the 4 clubs that never win

These need something other than "look how often you won" since the answer
is always zero, so pick the flavour that fits the piece:

1. **Best season (needs the new pass above).** "Best they ever managed: Nth
   place, in sim #X." The strongest, most literal answer to what you asked
   for — but the one option here that isn't free.
2. **Borrow from the flagged games (no new data needed).** All 4 clubs
   already appear in the current flagged-games set, just unevenly: Burnley
   14 times, West Ham and Wolves 3 each, Sunderland only 2. A non-winning
   club's card could show "their most memorable match across the
   1,000,000" pulled straight from `flagged-games.json`, filtered to games
   that club played in, regardless of result. Works for all four, but
   Sunderland's card would be picking from a much thinner set than
   Burnley's — worth knowing going in, even though it doesn't rule the
   option out.
3. **Reframe the zero.** Something drier and more data-native than a
   highlight: e.g. how close they got in title-odds terms to the next club
   up, or their average simulated finish vs. their real one (also needs the
   same new per-team pass as option 1, just averaged instead of best-of).

My instinct is (2) is the only one of these that's genuinely free to ship
as-is; (1) and (3) both want the same small backend addition first. Happy
to build that pass whenever you want it — didn't do it unprompted since it's
new scope beyond what's already shipped.

## Data for picking per club (the 16 that win)

You said you'd rather pick case-by-case than one blanket rule. Here's what
each club actually has on hand for the two free options above —
"comparison framing" just needs the numbers already in `treemap-data.json`
(no new data), "second story slot" needs one entry pulled from
`flagged-games.json` filtered to games that club played in (win or lose).

| Team | Real finish | Title odds here | Flagged games available |
|---|---|---|---|
| Arsenal | 1st | 71.69% | 649 |
| Manchester City | 2nd | 22.44% | 17 |
| Manchester United | 3rd | 3.44% | 121 |
| Liverpool | 5th | 0.88% | 160 |
| Bournemouth | 6th | 0.78% | 37 |
| Chelsea | 10th | 0.32% | 4 |
| Brighton | 8th | 0.11% | 4 |
| Brentford | 9th | 0.11% | 18 |
| Leeds | 14th | 0.09% | 7 |
| Newcastle United | 12th | 0.06% | 6 |
| Crystal Palace | 15th | 0.04% | 171 |
| Aston Villa | 4th | 0.03% | 268 |
| Tottenham | 17th | 0.01% | 1 |
| Everton | 13th | 0.00% (20/1,000,000) | 13 |
| Fulham | 11th | 0.00% (3/1,000,000) | 7 |
| Nottingham Forest | 16th | 0.00% (1/1,000,000) | 92 |

A few things worth knowing before you pick:

- **Arsenal is the real 2025/26 champion**, so "comparison framing" reads
  differently for them than for everyone else on this list — there's no
  "vs. 0% in reality" angle; it'd have to be framed some other way (e.g.
  against how often the *model* expected them to retain it), or just skip
  that option for Arsenal specifically and give them a second story slot
  instead.
- **Tottenham has only 1 flagged game** to draw a second story from — thin
  if you pick that option for them.
- Everything else has enough of a pool (4+) either way.

## Free option (c): reuse the curated tour's own stops

You spotted this one: the 9 curated-tour stops are each *about* a specific
club (attributing the two golden-boot stops to the scorer's own team, not
that sim's champion — Evanilson's stop is really Bournemouth's, not
whoever won the league that replay). `no_wins` is already spoken for (the
4 zero-win cards); the other 8 land on 6 distinct clubs, and since
`curated-tour.json` already carries full final tables/campaigns/scorecards
for every stop, a card for these could link straight to the existing
record — no new data pipeline, same as the zero-win cards already do.

| Stop | Club |
|---|---|
| fewest_wins | Nottingham Forest |
| golden_boot | Manchester City (Haaland) |
| unexpected_golden_boot | Bournemouth (Evanilson) |
| closest_final_week | Arsenal |
| biggest_margin | Arsenal |
| most_tied_first | Arsenal |
| lowest_gd | Leeds |
| closest_tiebreak | Newcastle United |

Arsenal has 3 candidates here (pick one); the rest have exactly 1. That
leaves **10 of the 16 winning clubs with no tour-stop freebie**: Manchester
United, Liverpool, Chelsea, Brighton, Brentford, Crystal Palace, Aston
Villa, Tottenham, Everton, Fulham — those are where the flagged-games
shortlist below actually matters.

## Flagged-game shortlist for the 10 clubs with no tour stop

Deduped to one example per *real* fixture (the raw counts in the table
above are dominated by the same handful of fixtures repeating across many
sims — e.g. nearly all of Crystal Palace's 171 are the same Liverpool
away day). Marked whether the club's own player has the haul ("theirs") or
it's the story of *conceding* one ("against them") — several of these are
memorable for the wrong reason, which may or may not be the flavour you
want on that club's own card.

**Manchester United** (11 distinct fixtures)
- #566,437 — Burnley 2–8 Man Utd — W — Sesko scores 7 (theirs)
- #20,042 — Man Utd 9–2 Burnley — W — Zirkzee scores 6 (theirs)
- #678,361 — Aston Villa 6–2 Man Utd — **L** — Morgan Rogers scores 6 (against them)

**Liverpool** (7 distinct fixtures)
- #55,105 — Liverpool 7–2 Brighton — W — Ekitike scores 6 (theirs)
- #86,838 — Liverpool 8–2 Newcastle — W — Ekitike scores 6 (theirs)
- #4,929 — Aston Villa 7–3 Liverpool — **L** — Ollie Watkins scores 6 (against them)
- #248,234 — Crystal Palace 8–9 Liverpool — W — plain high-scorer, no individual haul

**Chelsea** (3 distinct fixtures — thin)
- #17,872 — Chelsea 8–2 Leeds — W — João Pedro scores 6 (theirs)
- #406,302 — Fulham 7–1 Chelsea — **L** — Harry Wilson scores 6 (against them)
- #332,344 — Chelsea 5–10 Bournemouth — **L**

**Brighton** (4 distinct fixtures — thin, and all losses)
- #2,090 — Brighton 4–8 Man City — **L** — Haaland scores 6 (against them)
- #386,067 — Arsenal 7–0 Brighton — **L** — Saka scores 6 (against them)
- #55,105 / #43,307 — also losses, also conceding a 6-goal haul

**Brentford** (8 distinct fixtures)
- #2,035 — West Ham 0–8 Brentford — W — Thiago scores 6 (theirs)
- #37,300 — Brentford 7–0 Arsenal — W — Thiago scores 6 (theirs) — beating the real champion
- #656 — Brentford 7–4 Bournemouth — W — Kevin Schade scores 6 (theirs)

**Crystal Palace** (5 distinct fixtures)
- #509,023 — Crystal Palace 12–2 Bournemouth — W — Mateta scores **10** (theirs) — the single biggest individual haul in the whole million
- #648,813 — Crystal Palace 6–3 Everton — W — Sarr scores 6 (theirs)

**Aston Villa** (4 distinct fixtures)
- #678,361 — Aston Villa 6–2 Man Utd — W — Morgan Rogers scores 6 (theirs)
- #4,929 — Aston Villa 7–3 Liverpool — W — Ollie Watkins scores 6 (theirs)
- #269,077 — Aston Villa 10–5 Arsenal — W — beating the real champion, no individual haul

**Tottenham** (1 fixture — only option, and it's not flattering)
- #34,865 — Man Utd 9–0 Tottenham — **L** — Bruno Fernandes scores 6 (against them)

**Everton** (3 distinct fixtures)
- #337,847 — Fulham 7–8 Everton — W — plain high-scorer, no haul
- #168 / #648,813 — both losses, both conceding a 6-goal haul

**Fulham** (5 distinct fixtures)
- #588,609 — Newcastle 2–7 Fulham — W — Raúl Jiménez scores 6 (theirs)
- #406,302 — Fulham 7–1 Chelsea — W — Harry Wilson scores 6 (theirs)
- #15,777 — Fulham 11–4 Burnley — W — plain high-scorer

Every sim number above is real and pulled straight from
`flagged-games.json` — full scorecards already exist for all of them, same
as every other game-kind story already shipped.

## Status (2026-08-29, later) — second stories picked and wired

Your picks, now live as a second `roster-story-btn` on each club's card:

- **Crystal Palace** → the Mateta match (#509,023, `game` kind).
- **Aston Villa** → the 10-5 win over Arsenal (#269,077, `game` kind, full
  scorecard).
- **Tottenham, Fulham, Brighton, Brentford** → each club's own
  biggest-margin title win, not a flagged game (their flagged games were
  all unflattering — Tottenham's only one is a 9-0 defeat). New
  `build_champion_margin_stories()` in `export_treemap_data.py`, scoped to
  exactly these 4 (`OWN_BIGGEST_MARGIN_TEAMS`, a fixed editorial list, not
  a derived one), reusing the same table-metrics sweep as best-seasons —
  written to `articles/pl-treemap-data/champion-margin-stories.json`.
  Results: Tottenham win by 8 (sim #561,440), Fulham by 2 (sim #313,828),
  Brighton by 14 (sim #404,580), Brentford by 14 (sim #643,033).
- **Manchester United, Liverpool, Chelsea** → checked `flagged-title-ties.json`
  (37 total, all already on disk, no new pass needed) for whether they
  ever win the league on a tiebreak. All three do:
  - Man Utd: 10 candidates, 3 of them tied with *Arsenal* (the real
    champion) — picked #143,768 for the drama of that matchup; the other
    two Arsenal ties are #940,137 and #968,051 if you'd rather swap.
    (The other 7 are tied with Manchester City instead.)
  - Liverpool: only 1 candidate, #952,936 (tied with Manchester City).
  - Chelsea: 3 candidates, all tied with Manchester City — picked
    #457,242 (decided on away goals, the deeper/more dramatic tiebreak
    over the plain-head-to-head #77,997 / #888,773).

**Everton — resolved.** No flagged title-tie has them as champion, so the
tiebreak option didn't exist for them the way it did for the other three,
and you chose a plain league win over spending the ~3-minute rerun a
golden-boot check would've cost. Added to `OWN_BIGGEST_MARGIN_TEAMS`
alongside Tottenham/Fulham/Brighton/Brentford — same pass, no new code.
Result: Everton win the league by 4 points in sim #190,331. All 5 clubs
in that list, plus Crystal Palace/Aston Villa's flagged games and Man
Utd/Liverpool/Chelsea's tiebreaks, are now wired up. That's 10 of the 16 winning clubs done. The other 6 (Manchester City,
Arsenal, Bournemouth, Leeds, Newcastle United, Nottingham Forest) still
don't have a second button wired up — they're the ones with a free option
available (their own curated-tour stop, see above), just not yet actually
built into the roster the way this round's 10 are. Say the word and I'll
wire those too, same mechanism (`secondStoryByTeam`, already built to take
any story kind).

## Status (2026-08-29, final round) — all 16 wired, tour player retired

The remaining 6 clubs (Manchester City, Arsenal, Bournemouth, Leeds,
Newcastle United, Nottingham Forest) now reuse their own curated-tour stop
as their second story, exactly as flagged above as a free option — no new
data, `secondStoryByTeam` just picks the matching stop out of
`curatedTourRaw` (`TOUR_STOP_SECOND_STORY` in the HTML). Arsenal had three
stops to choose from (`closest_final_week` / `biggest_margin` /
`most_tied_first`, being both the real champion and a frequent one here);
picked `closest_final_week` for the title-race drama — swap it for one of
the other two if you'd rather. All 16 winning clubs now have a second
story button.

Two further changes, per your ask:

- **The treemap grid only highlights sims that actually have a story now.**
  Previously every entry in `flagged-champions.json` (1,985 "unexpected
  winner" sims), `flagged-games.json` (987), and `flagged-title-ties.json`
  (37) lit up as a clickable cell once zoomed into a team's grid — now
  only the ~25 sims actually referenced by a roster card or a curated-tour
  stop do. `flagged-champions.json` (a 13MB file) isn't even fetched by
  the page any more, since nothing on it survives as an individually
  featured story post-trim. `flagged-games.json`/`flagged-title-ties.json`
  are still fetched (needed to resolve Crystal Palace/Aston Villa/Man
  Utd/Liverpool/Chelsea's specific picks by sim number) but no longer
  drive blanket grid highlighting.
- **The guided-tour player is gone.** The start/pause/prev/next/exit
  controls, the auto-advancing itinerary, and the caption bar are all
  removed. In their place: clicking any roster card's story button now
  scrolls the treemap into view, zooms the camera to that story's actual
  cell, and opens the story modal once it lands (`zoomToStory()`,
  section 5 of the script) — the same one-cell-in-a-million payoff the
  tour used to deliver, just card-driven instead of an autoplaying
  slideshow. `curated-tour.json` itself is unaffected and still feeds
  both the grid highlighting above and the 6 reused-stop cards.
