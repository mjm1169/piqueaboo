# Piqueaboo — notes for Claude

See `README.md` for site structure, local preview, and deployment.

## Article authorship

On this site, the user writes article prose and originates visual/design
concepts. Claude's role is implementation: code, data pipelines, and
technical execution (scraping, simulation engines, chart mechanics, page
structure/CSS/JS plumbing) — not authoring headings, narrative copy,
captions, or inventing visual treatments on its own. Check with the user
for the actual text and visual direction before drafting either.

## due-date.html

- **2026-08-27, done — 50% labels on the dice chart, mode-line flash fix,
  and a real (not just visual) fix to the gestation chart's 50/50 split.**
  User feedback: reinforce the dice chart's 50/50 framing with the same
  blue/pink "50%" labels the gestation curve already carries, on both the
  prior-knowledge (`dice-half`) and updated-knowledge (`dice-newhalf`)
  steps; the mode marker ("most likely day") was flashing briefly when
  the gestation chart reappears after the dice section; and a request to
  check whether the gestation curve's two shaded areas are actually
  50/50, since the pink one visually looked bigger.
  **The pink area genuinely was bigger, not an illusion**: confirmed
  numerically before touching any code — `due-date-pdf.csv`'s own CDF at
  day 280 (the hardcoded due date, anchored to Naegele's-rule 40+0 weeks)
  is 0.4825, not 0.5, because this model's curve doesn't put its true
  median exactly on day 280 — a real, if small, mismatch between the
  clinical convention and what this particular smoothed curve says. Over
  the *displayed* range specifically (which excludes a sliver of mass
  before 35+0 weeks) that's a blue/pink split of 48.2%/51.8% — a ~3.7
  point gap, easily visible once both halves carry an explicit "50%"
  label. **Fix**: `MEDIAN_DAY` (used everywhere as "the due date" — the
  region split, the reference line, every label) is no longer hardcoded
  to 280; it's now `quantile((cdfAt(DISPLAY_MIN)+cdfAt(DISPLAY_MAX))/2)`
  — the day that bisects the *displayed* curve's own area exactly, which
  is what the article's own opening paragraph already defines a due date
  to be ("the median of the distribution... shown"). `MEDIAN_CALIBRATION`
  (existing, unchanged) still keeps the scrub's conditional-median maths
  aligned to this new value with no further changes needed, since it was
  already written generically. **Visible consequence worth knowing**: the
  "Due date" label now reads "40w + 1d" instead of "40w + 0d" (day 280.57
  rather than 280) — a deliberate trade for the areas being genuinely
  equal rather than a clean-but-wrong round number; nothing in the
  article's own visible prose asserts "exactly 40 weeks," so this doesn't
  contradict anything shown. A Playwright shoelace-area check on the
  actual rendered SVG paths confirmed the fix: left/right area ratio went
  from a clearly-visible ~1.077 (7.7% off) to ~1.008 (0.8% off, the
  residual coming from `areaPath()`'s pre-existing day-grid quantisation
  at STEP=0.25 days, present everywhere it's used and well under any
  perceptible threshold — not something this round rewrote). **Mode-line
  flash, root cause**: `renderDice()` never calls `clearRegions()` (that
  only runs inside `renderGestation()`), so leaving the gestation chart
  on the `mode` step left the mode marker's `.visible` class dangling the
  whole time the dice chart was showing — invisible only because its
  *ancestor* SVG was `opacity:0`. Returning to any other gestation step
  re-faded that ancestor in over `.12s`, far faster than the marker's own
  `.5s` opacity transition (which only *starts* once `clearRegions()`
  finally runs again) could fade it back out — a brief window where both
  were partway visible at once, reading as a flash. **Fix**: `showGroup()`
  now clears the mode marker's `.visible` class instantly the moment the
  gestation chart is hidden (switching to the dice group), rather than
  waiting for the next `renderGestation()` call — by the time a reader
  scrolls back, its fade-out finished long ago, so there's nothing stale
  left to flash. Verified by sampling the element's live computed opacity
  every animation frame across a scripted mode→dice→(a non-mode gestation
  step) transition: 77 samples, opacity 0 throughout, versus what would
  have been a visible mid-transition spike before the fix. **Dice 50%
  labels**: new `diceLabel()`/`showDicePct()`/`hideDicePct()` helpers
  reuse the gestation chart's own `.chart-label.pct` styling for visual
  consistency, recomputing each label's x from the *live* bar indices in
  its group every time (three bars each on `dice-half`, two each on
  `dice-newhalf` once 1 and 2 are ruled out) so they genuinely track the
  group's centre as it narrows, per the user's own note that this was a
  requirement, not just a nicety. Verified: label x confirmed to shift
  between the two steps (181.5→310 for blue, 438.5→481.3 for pink) rather
  than staying fixed, and hidden (as expected) on the transitional
  `dice-condition` step, which shows no 50/50 split. All four fixes
  screenshotted on both desktop and a 390px-wide mobile viewport — labels
  render cleanly, correctly centred, no clipping. Not yet pushed to
  `main` — left on `claude/pl-xg-article-commentary-cnrfz3` pending an
  explicit merge request.

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

  **2026-08-26, done — zoom engine rewritten around one continuous camera,
  fixing the "Other looks broken" report and the "zoom changes direction"
  complaint.** User feedback: clicking "Other" looked broken ("everything's
  on the left cut off"), and the zoom itself should be "smoother and not
  change direction" — one continuous motion in two stages (blocks, then
  individual squares coming into focus), always converging on one point.
  **Root cause of both**: the previous engine used two incompatible
  coordinate systems (an overview `ctx.setTransform` window vs. a separate
  `gridState.panCol/panRow/cellsAcross` system for a team's grid), bridged
  by a crossfade that swapped between them once a target block filled the
  canvas — that swap was the "direction change." Other's specific bug: its
  zoomed-in view (`otherBlocks`, squarified against the *full canvas*
  aspect ratio) and its overview-mosaic preview (`otherMiniBlocks`,
  squarified against Other's actual, much narrower overview rect) were two
  *different* layouts of the same teams — squarify's row/column choices
  depend on the container's aspect ratio — so the crossfade between them
  visibly rearranged blocks. **Fix**: `pl-xg-simulator.html`'s section 3
  (RENDER) and section 4 (ZOOM/GRID ENGINE) were rewritten around one
  nested world and a single `camera = {x,y,w,h}` window into it, magnified
  onto the canvas with the same `setTransform` trick throughout. Other's
  children are now squarified *inside Other's own rect* (one computation,
  reused for both the overview mosaic texture and the zoomed-in view — no
  second layout to mismatch against). A team's grid cell `(col,row)` is now
  just arithmetic on that team's own block rect (`x = block.x +
  (col/cols)*block.w`, etc.) rather than a separate pan/zoom system, so
  cells nest in the exact same coordinate space as every block. Every
  zoom — into a block, into Other, into a specific flagged cell, and back
  out — is the same `tweenCamera(fromRect, toRect)` converging on one
  target; there's no second coordinate system to swap to. Which block draws
  its flat colour+crest vs. its per-sim grid is now a live per-frame
  decision (`gridRevealAlpha`) that cross-fades in over a bounded range of
  "how many cells would span the camera" rather than a discrete mode
  switch — that's the "two stages" the user asked for (blocks, then squares
  coming into focus) without a second camera underneath it. One consequence
  worth flagging explicitly: Other is no longer a separate navigational
  "stop" you zoom into before picking a team from it — since its children
  are always rendered (even zoomed out, as the mosaic texture) and tile its
  rect with no gaps, a single click anywhere — a top-level block or one of
  Other's — now goes directly to that team's grid in one motion, and the
  back button is always exactly one hop (never a 2-level unwind). This is a
  simplification beyond what the agreed plan (`purring-finding-badger.md`)
  explicitly called for; it fell out naturally once Other's children had
  nowhere else to "pop" into, and it directly serves the user's "always
  zooming toward one point" ask, but is worth them knowing about since it
  does change the interaction shape slightly (was 2-step for a pooled team,
  now 1-step). Moving between two *different* already-zoomed teams (e.g. a
  tour stop jumping from one team to another) is still two chained tweens
  — out to the whole map, then in to the new team — since that's a
  legitimate "these are two different places" motion; each leg is still one
  camera converging on one target throughout, so there's no discontinuity
  within either leg.
  Desktop wheel-zoom/drag-pan and the mobile tour-tap flow were both
  re-pointed at the same `camera` fields (previously their own
  `gridState.panCol/panRow/cellsAcross` bookkeeping) — same bounds/behaviour,
  simpler underneath.
  **Verified**, not just eyeballed: all three inline `<script>` blocks
  syntax-checked; a temporary in-page debug hook (removed before
  finishing) sampled `camera`'s x/y/w/h every animation frame during a
  real zoom-in and confirmed it changes monotonically toward the target
  the entire time (no direction change, checked programmatically, not just
  by eye) and that the grid-reveal alpha ramps from 0 to a genuine 1.0 by
  arrival (an earlier tuning pass had the "fully opaque" threshold set
  *tighter* than the default block-click zoom target, so a plain click
  would arrive stuck at ~86% opacity forever — caught by this same
  sampling and fixed by loosening the threshold above
  `ENTRY_CELLS_ACROSS_CAP`). Clicking directly into Other now lands
  cleanly on a pooled team's full-bleed grid with nothing clipped
  (screenshotted); the full 20-stop guided tour, the mobile tap-in suite,
  and desktop wheel-zoom/drag-pan were all re-run against the rewritten
  engine and pass with zero findings.

  **2026-08-26, later — no more grid whitespace, zoom-depth floor,
  persistent crest badge, and pinch-zoom/pan on mobile.** Four more
  rounds of user feedback on the rewritten zoom engine above.
  **Grid whitespace**: `gridGeometry()`'s old `ceil(sqrt(n))` column count
  almost never divides `n` evenly, so the last row was partially empty --
  visible dead space inside a team's block once zoomed in (487 wasted
  cells out of Arsenal's 717,409-cell grid, worst case). New
  `gridDimensions()` searches a window of column counts around an
  aspect-aware estimate for the one that leaves the least waste, and the
  last row's cells stretch a little wider to fill the block's exact width
  regardless (`cellWidthForRow`/`colsInRow`, threaded through
  `drawGrid`/`hitTestGridCell`/`cellRect`). Same real teams verified by
  hand: Arsenal's waste dropped from 487 cells to 2; Fulham, Everton, and
  Leeds (889 wins) all landed at 0-2 wasted cells.
  **Zoom depth**: `targetRectFor()` had no floor on how tight a single
  zoom-in could get, so a team with only a handful of wins -- Fulham (3),
  Nottingham Forest (1) -- had a block only a few *world-units* wide,
  and the camera would zoom in by 1000x+ to fill the screen with 2-3 blank
  cells and nothing else ("zoom goes in too far in places"). New
  `MIN_ZOOM_DIM` (70 world units) floors the camera window size, and the
  clamp target changed from the block's own bounds (nonsensical once the
  window can exceed the block) to the full canvas, so a floored window
  centres on the target instead of pinning to one corner. Confirmed via a
  temporary in-page debug hook: Fulham's entry window went from
  0.57×5.23 (a ~2,000x zoom) to a sane 70×70.
  **Crest persistence**: entering any team's grid lost its crest entirely
  -- `drawGrid` only ever draws coloured squares, no per-team branding, so
  once zoomed in there was no visual reminder of *whose* grid you were
  looking at. Fixed with a small always-on-while-zoomed-in overlay badge
  (`#grid-crest-badge`, screen-space HTML/CSS, not canvas-drawn, so it
  stays crisp and correctly sized at any zoom depth) showing the current
  team's crest + name, pushed to the right end of the existing tour/back
  button row via `margin-left:auto`. Verified showing/hiding correctly
  through zoom-in, tour stops, and back-out, including for a barely-visible
  team like Fulham where it's the *only* on-screen identification once
  zoomed in (see the known gap below).
  **Mobile pinch-zoom/pan** (the user's explicit pick from three options
  put to them, over a cheaper tap-tolerance-only fix or a roster-card
  fallback): mobile previously had no way to zoom in before tapping, so
  precisely tapping one of Other's smaller pooled teams -- packed into a
  fraction of the canvas, no mouse-cursor precision to rely on -- could
  mean hitting a genuinely tiny target blind. New touchstart/touchmove/
  touchend/touchcancel handlers give one-finger pan and two-finger
  pinch-zoom, working at *every* level (root/Other included, not just once
  inside a grid like the existing desktop wheel/drag) -- reusing the same
  `camera` fields the mouse controls already write to, plus a shared
  `cameraZoomBounds()` extracted from the wheel handler for both to use.
  `#treemap-canvas`'s `touch-action` changed from `manipulation` to `none`
  so the browser's own default touch handling stays out of the way of the
  hand-rolled gestures. A `touchMoved` flag (mirroring the existing
  `didDrag` for mouse) suppresses the click a real pan/pinch gesture would
  otherwise leave behind. Verified: synthetic two-finger touch events
  confirmed pinch-out zooms in and pinch-in zooms out with no accidental
  block-selection afterward, and one-finger pan moves the camera without
  changing zoom level, both via a temporary debug hook (removed before
  finishing); the existing real-touchscreen-tap mobile suite
  (`test_mobile.js`/`test_mobile2.js`) still passes unchanged, confirming
  normal taps still navigate correctly and aren't swallowed by the new
  gesture handling.
  **Known gap, not addressed this round**: the crest badge fixes losing
  the team's identity, but doesn't fully fix "zoom too far" for a team
  whose block is extremely elongated relative to its own tiny size (Fulham
  is a 0.57×5.23 world-unit sliver) -- the 70×70 floor gives a sane zoom
  *magnitude*, but Fulham's own sliver can still end up a barely-visible
  line within that window, surrounded mostly by neighbouring teams' blocks
  rather than clearly framing Fulham itself. Flagging rather than
  over-fitting a fix to one pathological case; worth another look if it
  comes up again in practice.
  Verified end-to-end: full 20-stop guided tour, both mobile tap suites,
  desktop wheel-zoom/drag-pan (screenshotted before/after), and the
  Other-region flow all re-run against the final code with zero findings;
  all three inline `<script>` blocks syntax-checked with the debug hooks
  stripped out.

  **2026-08-27, done — exact zero-waste "notched" treemap, whole canvas as
  one 1,000,000-cell grid.** User feedback on the squarified-per-team grid
  above: it still wasted cells (a team's own grid rarely divides its exact
  `title_count` evenly into `cols x rows`), and after a first attempt at a
  centred/margin fix ("no wasted cells... fixed dimension grid, making
  slightly smaller rectangles and filling in the boundaries") the user
  pushed further with a hand-drawn reference image: no frame at all, the
  *whole canvas* should be one exact 1,000,000-cell grid where a team's
  shape is a near-rectangle and any leftover from its exact count is
  absorbed by the *adjacent* team's colour as a stepped "notch" at the
  shared boundary -- confirmed via `AskUserQuestion` as "whole canvas, one
  grid, but it should have the general look of a treemap, except at the
  boundaries which will contain notches." Planned in
  `/root/.claude/plans/purring-finding-badger.md` (approved as-is) and
  built accordingly. **Algorithm**: `squarify()` is gone, replaced by
  `notchedTreemap()` -- adaptive slice-and-dice peeling exactly *one* team
  at a time off a sorted list (not a whole strip at once, which is what
  keeps every boundary to exactly two teams), alternating column/row
  splits by aspect ratio same as before. Where a team's exact cell count
  doesn't divide evenly across its strip, the remainder becomes a
  1-cell-wide/tall notch (`fillColumn`/`fillRow`) that the *next* team's
  region absorbs, rather than leaving background. Every recursive call's
  invariant (`sum(items.value) === w*h`) holds exactly by construction --
  no rounding, no reconciliation pass. `peelForRegion`/
  `notchedTreemapMultiRegion` generalize this to a *list* of starting
  regions, needed because "Other" (still pooled the same way, still forced
  last in the ordering) turned out NOT to always land as a single clean
  rect -- being last only guarantees its *final* leftover is clean, not
  that it wasn't also pulled in earlier as `rest[0]` to absorb a preceding
  boundary's notch (confirmed happening on the real data: Other absorbed a
  1x44 notch from Manchester United's boundary in addition to its own main
  block). **What this simplified, beyond what the plan anticipated**:
  since 1 world-unit cell === 1 sim exactly, a team's layout parts *are*
  its individually-addressable cells -- no more separate per-team grid
  dicing (`gridDimensions`/`gridGeometry`/`colsInRow`/the old `cellRect`
  all deleted). Every part is now a plain, uniform `w*h` grid of unit
  cells by construction, so there's no ragged last row to special-case
  either. "Other"'s children are folded directly into the same flat
  `blocks` list used for top-level teams (no separate `otherBlocks`/
  `otherBlockByTeam`/`isPooled` any more) -- `hitTestRoot` and `render()`
  lost their Other-specific branches entirely. A team's up to 3 parts
  (main block + boundary notches) are looked up via `blockByTeam[team]`,
  bounded via a new `teamBounds()` helper (min/max over parts, used only
  for camera framing -- never for grid math, since a notch+main-block
  union doesn't fill its own bounding box), and crest/label drawing now
  happens once per team on its largest part (`mainPartByTeam`, via a new
  `drawTeamOverlay()` split out of the old `drawFlatBlock`) rather than
  being drawn inline per-block. **Verified**: a standalone Node script
  (`notchedTreemap`/`fillColumn`/`fillRow`/`peelForRegion`/
  `notchedTreemapMultiRegion`, mirroring the plan's pseudocode exactly)
  was run against the real per-team `title_count` values *before* touching
  the HTML at all, asserting programmatically -- not "looks close enough"
  -- that total area, every team's own cell count, zero overlap, and full
  coverage all hold exactly, at both the top level and Other's nested
  level, plus edge cases (50 tiny equal-value items, a single item filling
  everything). After porting into `pl-xg-simulator.html`: the identical
  exactness check re-run live against the page's actual constructed
  `blockByTeam` (not just the standalone script) confirmed 1,000,000
  cells total, 1,000,000 unique cells covered, 0 overlaps, on the real
  16-champion 2025/26 data (max 3 parts for one team -- Arsenal, which
  both gives a notch to Manchester City and separately its main block).
  A pinch-zoom test targeted exactly at a real notch (Arsenal's 1x122
  sliver at world x=896) confirmed via screenshot that Arsenal and
  Manchester City resolve into individual cells at the same moment right
  at that boundary -- the "all teams resolve at the same time" requirement
  from the second round of feedback, still holding under the new layout.
  Full regression re-run against the ported code: all three inline
  `<script>` blocks `node --check`ed clean; the full 20-stop guided tour
  (5 champion/5 title-tie/10 game stops, scorecards/campaigns/tiebreak
  blocks all correct); crest badge show/hide across zoom-in and back-out;
  desktop wheel-zoom and drag-pan; mobile pinch-zoom/pan
  (`test_touch.js`); both real-touchscreen-tap mobile suites
  (`test_mobile.js`/`test_mobile2.js`); and the "Other" region flow
  (click straight into a pooled team's real per-sim grid, confirmed via
  screenshot showing several pooled teams' grids resolved together at the
  shared boundary, then a single-hop back to the overview) -- all zero
  findings, aside from one pre-existing, unrelated Google Fonts network
  block in this sandbox (not caused by this change). Merged to `main`
  on explicit request.

  **2026-08-27, later — every team's cells now genuinely contiguous, plus
  a hover team-ID readout and crests restricted to the overview.** User
  feedback on the notched treemap above: (1) "some sections aren't
  touching" -- notchedTreemap's per-boundary notches are exact and
  gapless but were never actually proven contiguous, and in practice
  often weren't: a team's own given-away notch and a separately-absorbed
  notch each anchor to whichever boundary produced them, with nothing
  tying the two together. (2) asked for "a clean way to know what team
  you're looking at", explicitly leaving the approach to Claude and
  asking to keep it simple. (3) crests "go funny" on pan/zoom -- they're
  canvas-drawn in world units under the same camera transform as
  everything else, so mid-zoom they get magnified far past their native
  raster resolution (blurry/pixelated) before settling back down.
  **Contiguity**: spent a long stretch trying to make `notchedTreemap`
  itself provably contiguous (an "attach edge" threading scheme forcing
  each boundary-continuation to overlap its incoming fragment) -- each
  attempt fixed the case it targeted and broke a new one a few levels of
  nesting deeper (verified via increasingly large synthetic stress tests,
  not just the real 16-team data, since a future season's different
  title-count distribution could hit a case this season's numbers don't).
  Abandoned that path as unboundedly hard to make airtight and took the
  simpler, verifiable route instead: kept the *original* notchedTreemap
  completely unchanged (still exact/gapless/overlap-free, proven), and
  added a new post-process, `repairContiguity()`, operating on the
  already-correct output at the cell level. It rasterizes the layout to a
  1,000,000-cell `Int32Array`, and for any team whose cells land in more
  than one 4-connected blob, hands the smallest blob wholesale to
  whichever neighbour borders it most, then reclaims the same cell count
  by growing the team's main blob outward one ring at a time -- taking
  only cells currently on that neighbour's *outer* boundary, never
  tunnelling into its interior, so the swap can't carve a new hole in the
  neighbour. Runs to a fixed point (a reclaim can itself leave the
  neighbour freshly disconnected elsewhere), but only re-checks teams an
  actual swap touched rather than every team every pass, since re-scanning
  the whole grid for every team every iteration was the difference between
  ~0.4s and multiple minutes at this scale. The repaired grid is
  rasterized back into rects with adjacent identical-team row-runs merged
  into one taller rect as it goes (2,156 raw 1px rows -> 124 rects on the
  real data) so a repaired region reads as a handful of blocks, not a
  dense hairline-striped mess. **Verified two ways**: standalone stress
  tests (500+ synthetic layouts, both a general random spread and a
  sports-realistic skew, n up to 25-30 items) to catch cases the specific
  real season's numbers happen not to trigger; then the actual criterion
  that matters -- a true 4-directional flood-fill connectivity check
  (not rectangle-adjacency, which the earlier "1 disconnected team"
  finding turned out to undercount) run live against the page's real
  constructed `blockByTeam`: exact 1,000,000-cell area, zero overlaps,
  zero gaps, and every one of the 16 real teams a single connected
  component. **Team ID**: added a cursor-following hover label
  (`#treemap-hover-label`, desktop/`hover:hover` only) driven by the
  existing `hitTestRoot`, shown only at the overview (`!pathTeam` --
  the persistent crest badge already covers "zoomed into a team's grid").
  Chosen over baking bigger/more labels into the canvas because it works
  uniformly regardless of a region's size (many of the smallest teams'
  blocks are far too small to fit a label at all) and reuses hit-testing
  that already existed, rather than inventing a new mechanism. **Crests**:
  `render()`'s crest/label overlay now gated on a new `isFullyZoomedOut()`
  (camera within half a world-unit of the untouched `{0,0,CW,CH}` extent)
  instead of the previous `alpha < 1`, so a crest is present at the exact
  overview and gone the instant a zoom or pan begins, rather than staying
  magnified (and blurry) through the whole early part of a zoom-in.
  Verified: crest pixels visible in an overview screenshot, confirmed
  absent in a screenshot immediately after zooming into Arsenal's grid
  (only the small always-on `#grid-crest-badge` overlay remains, which is
  a fixed-size HTML element outside the canvas transform and was never
  affected by this problem). Full regression re-run against the final
  code: hover label correct over two different teams' regions; strict
  flood-fill connectivity holds after the crest/hover changes too;
  20-stop guided tour; crest badge show/hide; desktop wheel-zoom/drag-pan;
  mobile pinch-zoom/pan and both real-touchscreen-tap suites -- all zero
  findings bar the one pre-existing, unrelated Google Fonts block. Merged
  to `main` on explicit request.

  **2026-08-27, later still -- fixed 9-stop curated guided tour, replacing
  the old 20-stop auto-picked one.** The user specified the tour directly:
  fewest title wins; no title wins (best-ever finish, full table only);
  highest-scoring golden boot winner (game detail); most unexpected golden
  boot winner, i.e. fewest real-life goals (game detail); closest title
  race into the final gameweek (that gameweek's results); largest points
  margin of victory; lowest goal difference to win the league (full
  campaign detail, after an initial "no detail" instruction was reversed
  mid-review); most teams tied on points for first; closest title race
  decided by head-to-head/away goals. A "20 team highlights" idea in the
  same message turned out to be the separate, already-deferred roster-card
  feature (`notes/pl-xg-roster-card-candidates.md`) -- out of scope here.
  Confirmed with the user that every stop must carry a real `sim` index
  mapping onto an actual grid cell, same as every existing flagged-sim
  story (`team = byteToTeam[champions[sim]]`, `rank = rankOfSim[sim]` --
  the story's *subject* needn't be that sim's champion, exactly like a
  flagged game's stop already works). Of the 9, only "fewest wins" and
  the head-to-head tiebreak stop were answerable from data already on
  disk; the rest needed genuinely new per-sim tracking the big pass
  discards (a team's own position once folded into running totals; no
  season-long per-player goal tally existed at all) -- this was the "run
  the million again" the user flagged themselves, though it didn't need a
  full redo: `champions.bin` and the three flagged-*.json files stayed
  exactly as they were (`--skip-big-pass`), and two *new* sweeps
  (`run_table_metrics_sweep`, `run_golden_boot_sweep` in
  `simulations/export_treemap_data.py`) regenerate the *same* 1,000,000
  sims bit-for-bit via the existing per-match seeding, writing one new
  small output, `articles/pl-treemap-data/curated-tour.json` (9 records).
  **A real bug found and fixed during verification, not just a scale
  artifact**: the three new *targeted* single-sim regeneration helpers
  (`build_campaign_for_sim`, `build_final_matchday_detail`,
  `build_best_match_for_player`) originally requested a truncated
  `(sim_idx+1, n_shots)`-shaped draw to save compute, on the assumption
  (checked once, only for a single-array draw) that a smaller row count
  from the same seeded generator reproduces the larger array's prefix
  bit-for-bit. That holds for one array pulled off a fresh generator, but
  these functions draw `draws_h` then `draws_a` *sequentially* from the
  same per-match `rng_i` -- so `draws_a`'s starting position in the random
  stream depends on how many values `draws_h` consumed, which depends on
  the row count requested. A truncated shape and the full `(n_sims, ...)`
  shape everything else (champions.bin, the table-metrics sweep) was built
  with consume different amounts for `draws_h`, so `draws_a` desyncs and
  the function silently regenerates a *different, wrong* simulated season
  for that sim. Caught by hand-checking a targeted-regeneration campaign's
  own W/D/L/GF/GA sums against the "official" table row for the same
  (sim, team) from the table-metrics sweep -- they disagreed on 2 of 4
  campaign stops at dry-run scale (22 of Arsenal's 38 games differed from
  a from-scratch independent recompute). Fixed by requesting the full
  `n_sims` shape in all three helpers (matching how the already-trusted
  `run_big_pass_sweep2` always regenerates full-size campaigns), at the
  cost of some wasted rows -- cheap here since each helper only runs a
  handful of times, restricted to a handful of matches, not all 380.
  **Verified thoroughly given that bug**: after the fix, every
  campaign/table pair (fewest_wins, biggest_margin, lowest_gd,
  closest_tiebreak) hand-checked against a from-scratch recompute at both
  a 100,000-sim dry run and the real 1,000,000-sim production run;
  golden-boot season totals, the no-wins team's position, and the
  final-gameweek's before-table/results all independently recomputed and
  matched too. Frontend: `buildItinerary()` in `pl-xg-simulator.html`
  rewritten to fetch `curated-tour.json` and build exactly the 9 fixed
  stops in the user's order (the old `distinctTopN`/4-category logic is
  gone); `openStory()` gained new rendering for golden-boot stops (reuses
  the existing game-modal markup, reframed around the player rather than
  the match), the final-gameweek stop (a new before-table + 10 compact
  results block), and a `no_wins`/`most_tied_first`-aware version of the
  champion-shaped branch (a new `.story-team` table-row highlight, applied
  to the zero-win team's own row -- distinct from the existing
  `.champion` highlight so a non-champion "this is who the story's about"
  row is never confused with who actually won that replay). Verified via
  headless-Chromium Playwright: all 9 stops walked start to finish via the
  real Start/Next tour controls (not just direct `openStory()` calls),
  each modal's visible sections (game body vs. champion body, the
  final-week block, the campaign block, the tiebreak block, the
  story-team row count) checked against what that stop's `kind` should
  show -- zero findings; the existing pinch-zoom/pan, real-touchscreen-tap,
  and flood-fill-connectivity suites all re-run against the fresh
  production data and still pass. Captions/tags are Claude-authored
  mechanical copy from the numbers, same convention as every prior tour
  round -- worth the user's own pass once they've seen it live. Merged to
  `main` on explicit request.

  **2026-08-27, later still -- mobile team ID during freeform pinch/pan,
  and a hard bound on how far the camera can be panned.** User feedback:
  "how the user knows which team they're looking at when zoomed in on
  mobile" and "add a bound so a user can't pan miles away from the
  chart." **Root cause of the first**: touch pinch-zoom/pan (added a
  couple of rounds back) works at *every* level, including the root
  overview, with no tap required first -- so a mobile user can pinch-zoom
  straight into a team's individual cells without ever tapping to
  "select" one. The persistent crest badge (`#grid-crest-badge`) only
  ever looked at `pathTeam`, which stays null the whole time in that
  flow, and the cursor-following hover label is desktop-only by design
  (no true hover on touch) -- so nothing on mobile ever named the team
  during a pure pinch/pan gesture. **Fix**: `pl-xg-simulator.html` gained
  `currentGridTeam()` -- `pathTeam` if set (unchanged for taps/the tour),
  else hit-tests the camera's own centre point once the camera's off the
  untouched overview -- and `updateGridCrestBadge()`, called from the
  touch pan/pinch handlers on every move (not just at the explicit
  select/deselect points `updateControlsVisibility()` already covered),
  so the badge tracks whichever team is actually centred on screen live
  during a freeform gesture. **Second issue**: the one-finger touch pan
  and mouse-drag handlers wrote straight to `camera.x`/`camera.y` with no
  bound at all; pinch/wheel re-centring could push position out of range
  too. Added `clampCameraPosition()` (`camera.x/y` hard-clamped to
  `[0, CW-camera.w]`/`[0, CH-camera.h]` -- camera.w/h are already <= CW/CH
  by construction, so the range is never inverted) called once at the top
  of `render()` itself rather than sprinkled into every gesture handler,
  so it catches wheel, mouse-drag, and touch pan/pinch alike for free
  through the one function they all already call. **Verified**: a
  synthetic two-finger pinch-in dispatched via CDP with no tap first
  showed the badge naming the correct team (`pathTeam` confirmed still
  null throughout, proving it came from the new fallback, not an
  implicit select); repeated attempts to drag/pinch the camera far off
  in one direction (both touch, via CDP, and desktop mouse-drag) left
  `camera.x/y` sitting exactly on the world boundary rather than
  escaping it, with the canvas still showing real content afterward (not
  blank); the existing pinch-zoom/pan, both real-touchscreen-tap, and
  flood-fill-connectivity suites all re-run clean. One stale, unrelated
  test script from an earlier round (`test_v2_wheel_drag.js`, calling a
  function removed by the later notched-treemap rewrite) was found dead
  during this pass and replaced with a fresh desktop wheel-zoom/drag-pan
  check rather than fixed in place, since none of this round's changes
  touch what it was originally covering. Merged to `main` on explicit
  request.
