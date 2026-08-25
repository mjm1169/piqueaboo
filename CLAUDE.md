# Piqueaboo — notes for Claude

See `README.md` for site structure, local preview, and deployment.

## Article authorship

On this site, the user writes article prose and originates visual/design
concepts. Claude's role is implementation: code, data pipelines, and
technical execution (scraping, simulation engines, chart mechanics, page
structure/CSS/JS plumbing) — not authoring headings, narrative copy,
captions, or inventing visual treatments on its own. Check with the user
for the actual text and visual direction before drafting either.

## TODO

- `articles/pl-xg-simulator.html` — replaced (2026-08-24) with a new piece
  built around a 1,000,000-simulation treemap of the 2025/26 season, per
  the user's own visual spec (area-proportional treemap, one region per
  champion team, crest centered, click-to-inspect "story" simulations) plus
  a supporting section on Leicester's 2015-16 title (10,000 sims). The old
  article's "simulate it yourself" live client-side widget was re-added
  pointed at the 2025/26 data — `articles/pl-xg-simulator-data.json`
  now holds that season's shots (regenerated via `export_client_data.py`)
  rather than 2024/25's.
  As of 2026-08-24 the user has written the actual commentary for the
  intro (xG explainer + "data information" disclosure), the treemap
  section's framing paragraphs, and the Leicester paragraph — all dropped
  in as real `<p>` copy. Still outstanding, marked `<!-- HEADING: TBD -->`
  (or similar) in the HTML for the user to fill in themselves: the page
  title/h1, the treemap section heading, the simulator section's
  heading/intro copy, and the Leicester section heading. Two inline
  placeholders inside the user's own Leicester paragraph are also still
  theirs to finish: `xx%` (the actual simulated Leicester title odds —
  note the equivalent number is already computed live in
  `#leicester-stats`) and `(insert examples here)`. The treemap intro
  paragraph also still has a literal `20xx/xx` season placeholder.
  `index.html`'s teaser card for this article is still placeholder copy
  and wasn't touched by this pass.

  **2026-08-25, done — genuinely-1,000,000-cell zoomable treemap** (see
  `/root/.claude/plans/purring-finding-badger.md` for the full plan, agreed
  with the user): the "zoom through the treemap" idea above is now a real
  guided flythrough into individually-addressable simulation cells, backed
  by a three-tier save policy on the 1,000,000-sim run (who-won by default;
  full season table when the champion is an "unexpected winner" — real
  position outside the top half; full match detail when a game hits 15+
  total goals or a player scores 6+, the latter capped to one flagged
  instance per real fixture). Both parts are checked in:
  `simulations/export_treemap_data.py`'s big pass writes
  `articles/pl-treemap-data/flagged-champions.json` (2,002 sims) and
  `flagged-games.json` (1,023 sims: 987 high-scoring, 36 deduped 6+-goal
  hauls), each record carrying a real global `sim` index into
  `champions.bin`; `pl-xg-simulator.html`'s treemap script now builds a
  client-side spatial index from that, renders a per-team zoomed-in grid
  (virtualised to the viewport — cost bounded by canvas size, not by how
  many sims a team won) once zoomed in past a threshold, and drives a
  click-to-start guided tour through the most extreme flagged sims with
  play/pause/prev/next/exit controls and an on-demand story modal. Overview
  ↔ grid is a defined crossfade rather than one continuous coordinate
  system, per the user's "simpler zoomed out, detail on zoom in" steer.
  Desktop-first (wheel-zoom/drag-pan); mobile gets the overview, roster
  cards, and tour (camera tweens need no pointer input) but not manual
  grid pan/zoom, per agreed scope. Verified with a real headless-Chromium
  Playwright pass rather than just a syntax check — caught and fixed two
  genuine bugs that inspection alone had missed (an un-deduped itinerary
  that collapsed onto a couple of outlier teams/fixtures, and a CSS
  specificity bug where this page's own `display:flex`/`none` rules beat
  the browser's default `[hidden]{display:none}` at equal specificity, so
  two control clusters and an empty caption bar stayed visibly stuck on).
  The itinerary's captions are auto-generated from the numbers ("Team X win
  the league here — in reality they finished Nth.") — worth the user's own
  pass to hand-tune once they've seen it live, same as the rest of this
  article's copy.

  **2026-08-25, done — real tie-breaks, full scorecards/campaigns, "Other"
  grouping** (see `/root/.claude/plans/purring-finding-badger.md` for the
  full plan): replaces the simplified GD→GF→coin-toss tie-break with the
  real Premier League chain (GD, GF, head-to-head points, head-to-head away
  goals, coin flip standing in for a play-off), flags a title decided at
  head-to-head-or-later as its own story type, adds full ordered scorecards
  (player/minute/penalty) to flagged games, and full 38-game campaign logs
  (opponent, H/A, sim score, xG score) to flagged champions. **Backend**:
  `simulations/simulate_season.py` gained `build_h2h_fixture_index()` /
  `resolve_tied_group()` (the real tie-break chain, reused everywhere
  match-level detail is available) and per-shot minute/penalty arrays in
  `build_match_index()`. `simulations/export_treemap_data.py`'s big pass is
  now two sweeps: sweep 1 (unchanged in spirit, now seeds each match's
  draws independently via `SeedSequence([seed, match_index])` so sweep 2
  can regenerate any match's results bit-for-bit identically without
  replaying the whole match list) detects title-level ties and captures
  full scorecards on flagged games; sweep 2 resolves those pending ties via
  head-to-head and builds a 38-game campaign log for every flagged
  champion. New output: `flagged-title-ties.json`. The small story batch
  also gets the real tie-break chain (cheap there — full match detail is
  already retained for every sim at that scale). **Known gap, left as-is**:
  `simulate_season.py`'s own `run_simulation()`/CLI (used to generate
  `results/sim_leicester_2015_16.json`, shown in the article's Leicester
  stats box) was *not* touched and still uses the old simplified rule —
  the plan claimed this would be free to fix too, but `run_simulation()`
  doesn't retain match-level detail the way the small story batch does, so
  it isn't actually free; low practical impact (10,000 sims, a handful of
  aggregate stats, a top-position tie in that specific run is rare) but
  worth knowing about if picked up later. Full 1,000,000-sim regeneration
  verified end-to-end: 1,985 flagged champions, 987 flagged games, 37
  flagged title ties, all cross-checked by hand (campaign W/D/L/GF/GA sums
  match each champion's final table exactly, scorecards match the raw shot
  data's minutes/penalty flags exactly, all 7 title-tie resolutions
  verified by hand at dry-run scale before the full run).
  **Frontend**: `pl-xg-simulator.html` now renders all of the above —
  a grouped-by-player scorecard in the game modal ("Haaland (1', 31', 54'
  (p))"), a full 38-game campaign table (W/D/L, sim score, xG score) and a
  head-to-head explainer in the champion modal for title-tie stories, and
  the least-frequent champions (whoever makes up the smallest 5% of all
  sims combined) are now pooled into a clickable "Other" region with its
  own squarified sub-map — a new intermediate zoom level between the
  overview and a real per-sim grid, reusing the same crossfade mechanism as
  overview↔grid rather than a third bespoke transition. The camera tween
  duration is now viewport-aware (1400ms under the mobile breakpoint vs.
  650ms on desktop — the fixed speed read as too fast to track on a small
  screen with no cursor to anchor on). Verified with a real headless-Chromium
  Playwright pass: walked every one of the 20 guided-tour stops (5 champion,
  5 title-tie, 10 game) checking each modal's contents against its kind,
  scanned the canvas for the "Other" block's colour to click it, then
  scanned again for a sub-block to click into a real grid, and confirmed
  two "back" clicks correctly unwind grid→Other→overview. Caught and fixed
  two real bugs in the process: the same `style.display=''`-falls-back-to-
  stylesheet-default pitfall hit before (this time on the new campaign and
  tiebreak sections), and a stale itinerary-index assumption in the
  regression test suite (not a site bug) after the itinerary gained new
  stop kinds.

  **2026-08-25, later — Other cutoff to 3%, Other-zoom jank fix, sim
  numbers in captions; two markdown candidate lists left for tomorrow.**
  User feedback on the above pass, actioned same day: (1) `OTHER_CUTOFF_FRACTION`
  changed from 0.05 to 0.03 in `pl-xg-simulator.html` (same 17-team "Other"
  set on the current data either way — the gap between the smallest teams'
  cumulative total and the next team's inclusion straddles both
  thresholds). (2) The "Other" zoom-in read as janky (a flat grey block
  popping into a detailed sub-map) — fixed by pre-rendering "Other" itself
  as a mini mosaic of its own constituent teams' colours on the overview
  (new `drawOtherMosaic()`, called from `drawBlocks()` instead of a flat
  fill), using the exact same `squarify()` output scaled into Other's
  actual overview rect, so the crossfade into the full-scale sub-map now
  lands on (near enough) the same geometry instead of popping. (3) Tour
  captions and both story-modal subtitles now quote the sim number
  ("Sim #34,421 — Arsenal win the title on a tiebreak…") via a new
  `simTag()` helper — small, and shipped outright rather than left as a
  choice, per the user's ask.
  **Deliberately NOT done, per the user's own request to pick a shortlist
  themselves**: the tour itself is still all 20 stops (5 champion + 5
  title-tie + 10 game) — cutting it to 5 needs the user's picks first.
  `notes/pl-xg-tour-candidates.md` lists all 20 (sim number, teams/score,
  one-liner) for them to choose from; once they reply, trim `buildItinerary()`
  to just those 5 (or whatever count they land on) — that's the one
  concrete follow-up this note leaves open. Also **not done**, explicitly
  lower priority per the user ("we can talk about that later"):
  `notes/pl-xg-roster-card-candidates.md` sketches ideas for richer roster
  cards, including the user's own "best season" idea for the 4 clubs that
  never win in 1,000,000 sims (Burnley, Sunderland, West Ham, Wolves) —
  flagged there as needing a small new backend pass (best-position-per-team
  isn't in any saved output today, since ordinary sims discard a team's
  position once folded into the running totals), alongside two candidates
  that need no new data. **Investigated, not a code bug**: "I'm still not
  seeing any game level details" — re-scanned for the `style.display=''`
  pitfall (none found) and re-ran the full scorecard-rendering check across
  all 10 game stops (all correct: player/minute/penalty grouping renders
  right). Working theory, given the tour is 20 stops long and the 10 game
  stops are all in the back half (positions 11–20): the user likely hadn't
  scrolled/played that far into the tour yet, not a rendering bug. Noted in
  `pl-xg-tour-candidates.md` too, since cutting to their chosen 5 (assuming
  at least one game-kind stop makes the cut) should resolve it either way.
  Verified via headless-Chromium Playwright: full 20-stop walk (all modal
  kinds/contents correct, 0 findings), then a corrected "Other" pixel-scan
  (the old flat-colour scan no longer matches now that Other is a mosaic;
  rewrote it to find the region structurally instead) confirming
  overview → Other → a pooled team's real per-sim grid → back → back
  round-trips correctly, plus the existing desktop/mobile suites all still
  pass. Nothing pushed to `main` this round — this work is left on
  `claude/pl-xg-article-commentary-cnrfz3` pending the user's picks from
  the two notes above.
