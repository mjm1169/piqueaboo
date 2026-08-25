# Roster card content: candidate ideas

You said the roster cards (the grid below the treemap, one card per club)
feel thin, and floated the idea of showing a "best season" for clubs that
never win in the 1,000,000 sims. Lower priority — for whenever you want to
pick this up.

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
