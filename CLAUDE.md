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
  render cleanly, correctly centred, no clipping. Merged to `main` on
  explicit request.

- **2026-08-30, done — dice labels above the bars, moving 50% labels on
  the scrub chart, and a real mobile-only sync bug behind the "38-week
  commentary" report.** Three pieces of user feedback.
  **Dice labels**: `DICE_PCT_Y` was vertically centred *inside* the bars'
  own height (straddling the coloured fill); moved to sit a fixed 18px
  above the bars' shared top edge instead — plenty of headroom already
  existed there since the bars only ever reach 62% of the chart's own
  vertical space.
  **Scrub chart 50% labels**: the continuous "today" scrub
  (`renderTodayContinuous`) shaded the same 50/50 split the static
  `regions` step does, but never labelled it — only the static step had
  "50%" text (`lbl-left50`/`lbl-right50`, fixed at `quantile(0.25)`/
  `quantile(0.75)`). Added a new `conditionalQuantile(todayDay, p)`
  (generalises the existing `conditionalMedian` to any p, not just 0.5)
  and call it every frame in `renderTodayContinuous` with p=0.25/0.75 for
  the two regions' own centres — reusing the *same* label ids as the
  static step (never active at the same time) rather than inventing new
  ones. Verified the labels' x-coordinates genuinely shift right as the
  scrub advances (e.g. left label 267.6→400.5 px across the scrub) rather
  than staying fixed, and screenshotted three points through the scrub
  confirming both labels stay legible and centred in their own
  (narrowing) region even near the very end.
  **Mobile "38-week commentary" desync — real root cause, not the
  suspected one**: first hypothesis (today-38/39/41's rendered heights
  differing, throwing off `pickScrubStep`'s equal-day-thirds assumption)
  was checked and ruled out — all three measured exactly equal on both
  mobile and desktop. The real bug: `calibrateScrubTiming()` sizes
  `#pin-wrap` (the sticky 'return' text's container) to `pinDays*rate`px
  and `updateScrub()` treats that *entire* height as "how long 'return'
  stays visually pinned" — but a `position:sticky` child only stays stuck
  for `(wrapperHeight - childHeight)` px after it engages, not
  `wrapperHeight` px (standard CSS sticky mechanics: release happens once
  the wrapper's bottom edge scrolls up to the stuck child's own bottom
  edge). On desktop the sticky child is ~100vh tall, close enough to
  whatever gets calibrated there that this was never very visible; on
  mobile, `.step.pin-step`'s height is capped to `100vh` *minus* the
  sticky chart band's own 36vh, so the child is far shorter than the
  wrapper — confirmed directly (dispatched real scroll positions and
  watched `return`'s own `getBoundingClientRect().top`): it unstuck and
  started scrolling normally ~300px into a wrapper calibrated for ~790px,
  meaning `today-38`'s paragraph was scrolling into view, and getting
  read, while `updateScrub()` still thought the reader was deep in the
  pin phase — the chart showed ~37w while the on-screen text already
  said "Say we reach 38 weeks". **Fix**: pad `#pin-wrap`'s calibrated
  height by the sticky child's own measured height
  (`stickyReturnHeight()`, new helper) so the *real* release point lands
  exactly at `pinDays*rate`; correspondingly, `updateScrub()` now splits
  `scrubPinWrap.offsetHeight` back into a `pinHeight` (minus that same
  gap) and folds the gap onto `runupHeight` instead — attributing the
  dead scroll after the real release point to "still blank, still
  advancing toward 38w0d" rather than "still pinned", without changing
  their sum, so the milestone phase's own boundary (and its already-
  working day-rate) is completely untouched. Deliberately a general fix
  (grounded in real sticky-release mechanics, not a mobile-only special
  case), so desktop's calibration becomes exactly consistent too, not
  just mobile's. **Verified empirically before and after**: a dense
  60-sample sweep through the whole mobile milestone track, measuring
  which of today-38/39/41 actually has the most on-screen overlap with
  the readable (below-chart) strip at each point (not just "nearest",
  which gives false positives for off-screen elements) — before the fix,
  `today-38`→`today-39` crossed over at day 264.0 against an intended
  milestone boundary of 266 (and, worse, `today-38`'s text was already
  dominant on screen from as early as day ~257, nowhere near 38 weeks);
  after the fix, the same crossover lands at day 265.8, essentially exact.
  Binary-searched the precise scroll position where the chart first shows
  "37w + 6d" (one day short of the milestone) and screenshotted it: the
  full, un-clipped `today-38` paragraph ("Say we reach 38 weeks...") is
  now the dominant on-screen text at that exact point, not a fragment cut
  off mid-sentence with the chart lagging a full week+ behind as before.
  Full page scroll-throughs on both viewports (200px increments) with a
  page-error listener attached confirmed zero JS errors from any of the
  three changes.

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

  **2026-08-27, later still -- root-level zoom depth, and de-zigzagging
  the notch-repaired boundaries.** User feedback from a mobile screenshot:
  "the zoom limit should allow more zoom," "the pan boundary should be
  bigger so I could pan to the cells in the corners," and a visibly
  crenellated Manchester City/Manchester United boundary ("there
  shouldn't be zigzag boundaries like this, the light blues could all be
  together"). **Zoom depth**: `cameraZoomBounds()`'s root-level floor
  (`pathTeam` null -- reachable on mobile via freeform pinch, which
  works at every level with no tap required first) was a much coarser 30
  world units than the `MIN_CELLS_ACROSS` (3) every zoomed-in team's own
  grid already allowed -- an old, undocumented asymmetry that mobile
  pinch was the only way to actually hit, since desktop wheel/drag are
  gated behind `pathTeam` already being set. Now the same floor
  everywhere. **Pan boundary**: investigated thoroughly rather than
  assumed -- a synthetic CDP pinch-then-drag test confirmed the existing
  clamp (added last round) already reaches every true corner exactly
  (`camera.x/y` lands on `0`/`CW-w` precisely) and a real team is
  identifiable there once zoomed in; a first test run that suggested
  otherwise turned out to be the test's own gesture budget too small for
  how many screen-pixels a drag needs at a *tight* zoom window (the same
  "Google Maps zoomed in needs many swipes to cross a big distance"
  effect, not a bug), and a second flaw where a pinch anchored inland of
  the true corner naturally re-centres there instead (correct pinch
  behaviour). Concluded this was the same root cause as the zoom-depth
  complaint, not a second bug -- left the clamp itself untouched, since
  loosening it would undo the previous round's explicit "can't pan miles
  away" fix. **Zigzag boundaries**: root-caused before writing any fix --
  a full-grid scan (rows/columns where run-count exceeds distinct-team-
  count, the actual signature of interleaving, not just "more than 2
  runs" which many *normal* multi-team-meeting rows also have) found
  the pathology confined to exactly 4 rows, each with one localised
  "pocket" where two teams' cells alternate in many small slivers,
  always sandwiched between already-clean runs. Root cause:
  `repairContiguity()`'s ring-growing reclaim, resolving several
  separate small orphan fragments along the *same* seam row (two big
  blocks stacked vertically, plus unrelated leftover notches all
  reassigned to whichever of those two borders them), nibbles a few
  cells from a slightly different spot each time rather than extending
  one clean edge -- correct (every team still one component overall) but
  visually a comb. Fix: a new post-process, `smoothInterleavedSeams()`,
  detects each pocket and consolidates it into (at most) two clean
  blocks, each team keeping its own existing cell count in that pocket
  (so no area/exactness invariant is touched) -- purely a reordering.
  Getting the *left/right order* right took two attempts: the first cut
  (whichever team has more cells in the row above wins the left side)
  passed 2 of 4 pockets and silently reverted the other 2 (a per-pocket,
  not all-or-nothing, safety check -- confirmed broken instances stay
  broken while the *other* pockets still improve) because "more cells
  above" can trivially go to a team with full-width presence there even
  when the *other* team is the one anchored to a specific edge below.
  Fixed by testing each team against the pocket's own left/right edge
  columns directly (does it occupy that exact column in the row above or
  below), which correctly identified the edge-anchored team in every
  case; the raw above-count comparison is now only a fallback for a
  genuinely ambiguous pocket. **Verified**: total "excess" alternating
  transitions across the whole grid dropped from 78 to 2 (the 2
  remaining are a harder 3-team interaction the 2-team pocket model
  doesn't fully resolve -- flagged as a known, much-diminished residual
  rather than chased further); the full strict flood-fill connectivity +
  exactness check still holds (1,000,000 cells, 0 overlaps, 0 gaps, all
  16 teams one component each -- unaffected, since the fix never changes
  any team's total cell count) with `maxParts` per team dropping from 22
  to 4; a direct screenshot of the Manchester City/Manchester United
  boundary before and after confirms a flat, clean line replacing the
  crenellated one. Re-ran the existing pinch-zoom/pan, both
  real-touchscreen-tap suites, the full 9-stop guided tour, and desktop
  wheel-zoom/drag-pan against the changed code -- all zero findings bar
  the one pre-existing, unrelated Google Fonts block. Merged to `main`
  on explicit request.

  **2026-08-29, done — "best season" roster cards for the 4 zero-win
  clubs.** Per the user's pick from `notes/pl-xg-roster-card-candidates.md`.
  Cheaper than that note flagged at the time: the per-sim, per-team
  position tracking needed already existed as a byproduct of the curated
  tour's own "no wins" stop, just discarded after picking the single
  best-of-4 team for that one tour slot. New `build_best_seasons()` in
  `export_treemap_data.py` keeps all 4 (full final table + 38-game
  campaign log each), written to `articles/pl-treemap-data/best-seasons.json`
  via a new `--skip-best-seasons` flag (the underlying table-metrics sweep
  is now shared between this and the curated tour, only skipped when both
  are). `pl-xg-simulator.html`'s roster now renders a real card for each
  zero-win club (`.roster-card.zero`, a CSS class that already existed but
  was never wired up) with a "Best-ever finish" button into the same
  story-modal path the tour's own no-wins stop already used; the old
  one-line "never won it: A, B, C, D" summary text is gone, replaced by
  the 4 cards. **Aside, not acted on**: regenerating `treemap-data.json`
  (an unconditional side effect of running the export script at all)
  produced different `stories[].notable_games`/`games` content than what's
  currently committed, despite an unchanged shots CSV and a confirmed-
  deterministic story-batch pass in isolation (two back-to-back runs in
  the same process matched exactly) -- likely tie-break sensitivity in
  `np.argsort`'s (unstable) quicksort differing across whatever numpy
  build originally generated the committed file vs. this `.venv`'s numpy
  2.0.2, given how many integer ties a 20,000-sim goal-count batch
  produces. Reverted that file rather than ship an unexplained change;
  worth a closer look if the story batch is revisited, but out of scope
  here. Also left open: which framing (comparison-to-reality vs. a second
  flagged-game story) to use for the 16 clubs that *do* win -- the user
  wants to pick per club, not one blanket rule; a table of each club's
  real finish/title odds/flagged-game count is now in
  `notes/pl-xg-roster-card-candidates.md` for that.

  **2026-08-29, later — second roster-card stories, picked per club.**
  User picks, now wired as a second `roster-story-btn` on each card (data
  in `notes/pl-xg-roster-card-candidates.md`): Crystal Palace and Aston
  Villa get a specific flagged game each (Mateta's 10-goal haul; the 10-5
  win over Arsenal); Manchester United, Liverpool, and Chelsea get a
  specific flagged title-tie each (all three do win the league on a
  tiebreak somewhere in the existing `flagged-title-ties.json`, no new
  pass needed -- Man Utd's pick ties with Arsenal specifically, for the
  drama of beating the real champion on a tiebreak). Tottenham, Fulham,
  Brighton, and Brentford get something new instead of a flagged game,
  since all of theirs read as unflattering (Tottenham's *only* flagged
  game is a 9-0 defeat): their own biggest-margin title win. New
  `build_champion_margin_stories()` in `export_treemap_data.py`, scoped to
  exactly those 4 clubs (`OWN_BIGGEST_MARGIN_TEAMS`, a fixed editorial
  list, not a derived one -- distinguishing it from `zero_win_teams`),
  reusing the same table-metrics sweep as `best_seasons` rather than a new
  one, written to `articles/pl-treemap-data/champion-margin-stories.json`
  via a new `--skip-champion-margin-stories` flag. Also added
  `--skip-story-pass`, since running the export script for any of this
  round's additions kept unconditionally rewriting `treemap-data.json`
  (previously worked around by just `git checkout`-ing it back afterward)
  -- the story-batch pass and its output are now properly skippable like
  every other stage. **Still open**: Everton has no flagged title-tie as
  champion, so it has no equivalent free pick; a golden-boot-per-club
  check would need a new query added to the (otherwise already-built)
  golden-boot sweep, not done unprompted since it costs a ~3-minute rerun.
  **Resolved same day**: user chose a plain league win over that rerun --
  Everton added to `OWN_BIGGEST_MARGIN_TEAMS` (win the league by 4 in sim
  #190,331), same pass, no new code. 10 of the 16 winning clubs now have a
  second card story; the remaining 6 (Manchester City, Arsenal,
  Bournemouth, Leeds, Newcastle United, Nottingham Forest) still have a
  free option available (their own curated-tour stop) but aren't wired up
  yet.

  **2026-08-29, later still — last 6 clubs wired, grid highlighting
  trimmed to only sims with a story, guided-tour player retired.** Per
  the user's ask. (1) The remaining 6 winning clubs each now reuse their
  own curated-tour stop as their second roster-card story (`no_wins` used
  the same trick already; `TOUR_STOP_SECOND_STORY` in the HTML just picks
  the matching stop out of `curatedTourRaw` -- no new data). All 16
  winning clubs now have a second story button; full picks in
  `notes/pl-xg-roster-card-candidates.md`. (2) The treemap grid used to
  highlight *every* flagged-champions/flagged-games/flagged-title-ties
  entry (1,985 + 987 + 37) as a clickable cell once zoomed into a team's
  grid; now only the ~25 sims actually referenced by a roster card or
  curated-tour stop get flagged (`flaggedByTeam`'s construction in
  section 1 of the script rewritten to source from those instead).
  `flagged-champions.json` (13MB) is no longer even fetched, since none of
  it survives as an individually featured story post-trim.
  (3) The standalone guided-tour player (start/pause/prev/next/exit,
  auto-advancing itinerary, caption bar) is removed outright. In its
  place, `zoomToStory()` (new, section 5) is the single entry point every
  roster-card story button now goes through: scroll the treemap into
  view, zoom the camera to that story's real cell via the same
  `zoomIntoTeam()` manual pinch/click already used, then open the story
  modal once the tween lands -- the cards now deliver the "one cell in a
  million" payoff directly, card by card, rather than needing a separate
  autoplaying tour. `curated-tour.json` itself, and its 9 records, are
  unaffected -- still feeds both the trimmed grid highlighting and the 6
  reused-stop cards above.

  **2026-08-29, later still — treemap seams/corners, tap-to-ID, label
  overflow, story-card delay, full-campaign table spacing.** Six pieces
  of user feedback from two screenshots (a mobile full-campaign table,
  and the treemap overview). **White lines on the treemap**:
  `drawFlatBlock` used to stroke a white hairline around every part it
  drew; `repairContiguity` can (and after the de-zigzag pass, still
  sometimes does) hand a single team back as several adjoining rects
  rather than exactly one, and each got its own stroke -- drawing a
  visible seam *inside* what should read as one solid team region, not
  just between different teams. Removed outright; plain fills read as
  clean block colour at every zoom level, matching the user's explicit
  "or even be block colours" fallback. **Rounded corners**: removed
  `#treemap-canvas`'s `border-radius:6px`, which was clipping the corner
  cells with a visible rounded cut-out against the card background.
  **Tap-to-ID**: the click handler's `gridRevealAlpha() >= 0.5` branch
  only ever updated the crest badge when the tapped cell had a story
  attached (via `zoomIntoTeam`/`openStory`); a tap on a plain, unflagged
  cell belonging to a *different* team than the current `pathTeam` (the
  two can meet on screen once zoomed in, at a team boundary) did nothing.
  Now sets `pathTeam` and calls `updateControlsVisibility()` on any such
  tap, not just ones that open a story. **Label overflow**:
  `drawTeamOverlay`'s team-name label was a fixed 13px regardless of
  block width -- Bournemouth's name overflowing its own narrow block was
  the case that showed it. Now shrinks the font (via `ctx.measureText`)
  down to a 9px floor to fit the block's width, and skips the label
  entirely rather than draw it clipped if it still doesn't fit at the
  floor. **Story-card delay**: `zoomToStory()` used to call `openStory()`
  the instant the camera's tween landed, covering the highlighted cell
  before it registered. Now waits a further 500ms after arrival before
  opening the modal, per the user's explicit spec ("zoom in, see the
  cell, pause 500ms, then the card"). **Back button**: shortened
  "← Back to the whole map" to "← Back", and the mobile
  `.treemap-overlay-controls` media query (which lays the row out in
  normal flow directly below the canvas on narrow screens) gained a
  `margin-top` alongside its existing `margin-bottom` -- it previously had
  nothing keeping it off the canvas's own bottom edge. **Full-campaign
  table**: browser auto-layout let the unlabelled result column (a bare
  W/L/D letter, no header) and the two-value score/xG columns size
  themselves inconsistently row to row, and on mobile widths let the xG
  column's "0.92–1.44" shape wrap onto two lines, misaligning every row's
  height. Switched to `table-layout:fixed` with explicit per-column
  widths (opponent gets the remaining space and ellipsis-truncates a long
  name like "Wolverhampton Wanderers" if needed; every numeric column
  gets a width wide enough to show full precision, confirmed by
  measuring actual rendered `scrollWidth` against `clientWidth` for real
  campaign rows rather than eyeballing it -- an early pass sized the
  mobile xG column 3px too narrow and still silently ellipsis-truncated
  every xG value, caught only by that measurement, not by looking at a
  screenshot).
  **Verified** via headless-Chromium Playwright rather than just
  eyeballing the diff: real desktop/mobile screenshots (including a
  high-DPI crop of the Man Utd/Man City/Bournemouth corner) confirm no
  white seams and no rounded canvas corners, and Bournemouth's label now
  fits inside its own block; a synthetic click dispatched at a real
  screen coordinate (computed from the live camera transform, landing
  provably on `CANVAS#treemap-canvas` via `elementFromPoint`, on a cell
  with no flag) onto a *different* team's cells than the current
  `pathTeam` confirmed the crest badge and `pathTeam` both update to the
  tapped team; a mobile roster-card story click measured ~3.9s from tap
  to modal-open, consistent with the ~1400ms mobile zoom tween plus the
  new 500ms pause (not just present in the diff); and per-cell
  `scrollWidth`/`clientWidth` measurements on 20 real campaign rows at a
  390px viewport confirm zero truncation on any Score/xG cell (only the
  one genuinely long opponent name truncates, by design). Pushed to
  `claude/pull-latest-main-m1y2cg`, then fast-forward merged to `main` on
  explicit request the same round.

  **2026-08-29, later still — zoom animation (pause, depth, easing),
  W/D/L replacing GF/GA, home-team-first score order, W/D/L result
  badges, golden-boot game-by-game.** Six pieces of user feedback in one
  round. **Whole-map pause between two zoomed views**: `zoomIntoTeam`'s
  cross-team path (zoom out, then in to somewhere new) chained the two
  tweens back-to-back with nothing between them; added a
  `WHOLE_MAP_PAUSE_MS` (500ms) `setTimeout` between `zoomOut`'s callback
  and the second `zoomIntoTeam` call, so a reader gets a beat at the
  untouched whole map before the next zoom-in starts. **Zoom depth**: the
  story-target camera window was silently dominated by `MIN_ZOOM_DIM`
  (70 world units) -- a floor meant for a plain team-explore zoom (no
  specific cell, just "look at this team") that happened to be much
  larger than `TARGET_CELLS_ACROSS` (9), so a story's own highlighted
  cell always arrived inside a 70-wide window regardless of the smaller
  number, making it a barely-visible speck. New `STORY_MIN_ZOOM_DIM`
  (= the also-tightened `TARGET_CELLS_ACROSS`, now 6) applies only when
  a specific cell is targeted; a plain team-explore zoom still uses the
  original `MIN_ZOOM_DIM`. **Easing**: turned out to already be a proper
  ease-in-out cubic (`easeInOutCubic`), applied via `tweenCamera` to
  every automated zoom already -- confirmed, not assumed, by sampling
  `camera.w` every animation frame through a real zoom-in and inspecting
  the frame-to-frame deltas, which grow smoothly from ~0 to a peak then
  shrink smoothly back to ~0 (a clean slow-fast-slow curve). No code
  change needed there; left as-is rather than churn something already
  correct. **W/D/L instead of GF/GA**: neither was tracked anywhere in
  `export_treemap_data.py` -- only points/gf/ga. Added win/draw/loss
  accumulation (vectorised, alongside the existing points/gf/ga sums) to
  both `run_big_pass_sweep1` (plus a `_pre` variant in
  `run_table_metrics_sweep`, for the closest-final-week "before" table)
  and threaded the three new arrays through `build_final_table` (now
  `w`/`d`/`l` fields) and all ten of its call sites. Caught a real bug
  while wiring this up: the first attempt named the new arrays
  `wins`/`draws`/`losses` in `run_big_pass_sweep1`, but that function's
  own haul-detection loop already reuses a bare `draws` as its loop
  variable (`for draws, players, team, opponent in (...)`) -- silently
  rebinding the accumulator to a `(n_sims, n_shots)`-shaped array for the
  rest of the function and crashing with an out-of-bounds index a few
  lines later. Renamed to `win_count`/`draw_count`/`loss_count` inside
  that function to avoid the shadow (the returned dict's keys stay
  `wins`/`draws`/`losses`, so nothing downstream needed to change).
  `pl-xg-simulator.html`'s two `.final-table` instances (final table,
  and the pre-final-gameweek table) now render W/D/L columns instead of
  GF/GA, keeping Pts/GD. **Home-team-first score order**: `renderCampaign`
  was displaying `sim_goals_for–sim_goals_against`, which is the
  campaign's own team's perspective (needed to work out W/D/L), not the
  match's home/away order -- an away game showed the tracked team's own
  score first regardless of whether they were home or away. Fixed
  entirely in the frontend (the backend fields were already sufficient,
  no regen needed for this one): swap for/against into home/away using
  the existing `e.home` flag before rendering. **W/D/L result badges**:
  replaced the old unlabelled text cell + coloured-left-border-only
  signal with a small circular badge (green/grey/pink via the existing
  `--positive-step`/`--muted`/`--negative-step` tokens, carrying the
  W/D/L letter) as the campaign table's first column, per the user's
  explicit colour spec. **Golden-boot game-by-game**: golden-boot stops
  only ever carried the scorer's own showcase match, no season-long
  view. `build_curated_tour`'s golden-boot loop now also calls the
  existing `build_campaign_for_sim` for the scorer's own team, adding a
  `campaign` field data-only, same targeted-regeneration helper every
  other campaign-carrying record already relies on. Rendering this
  needed a second DOM home for the campaign table
  (`#modal-game-campaign-block`/`-body`, inside `#modal-game-body`) since
  the original `#modal-campaign-block` lives inside `#modal-champion-body`,
  which is hidden for a golden-boot story -- a descendant's own
  `display:block` has no effect under a `display:none` ancestor, the
  same pitfall CLAUDE.md has flagged before on this page. `renderCampaign`
  gained optional `blockId`/`bodyId` parameters (defaulting to the
  original champion-body ids) so both call sites share one render path;
  the plain `'game'` kind (a flagged game with no campaign) explicitly
  calls it with `null` too, so a stale golden-boot campaign table can't
  linger visible if a reader opens a plain game story right after.
  **Backend regeneration**: needed the full 1,000,000-sim pipeline
  rerun (both the big pass and the table-metrics sweep embed
  `final_table`), verified extensively before and after committing to
  the full run -- a 100k-sim dry run first (every `final_table` row's
  w+d+l=38, 3w+d=points, and gf-ga=gd checked programmatically; every
  campaign's own derived W/D/L cross-checked against its team's
  `final_table` row, exact match), then after the real run: `git status`
  showed `champions.bin` and `flagged-games.json` byte-identical
  (confirmed via md5sum against the committed version) and every other
  touched file's set of flagged/curated `sim` values exactly unchanged
  from the previously-committed data (0 added, 0 removed, spot-checked
  fields matching) -- confirming the change was purely additive, nothing
  about which sims get flagged or picked was disturbed. `treemap-data.json`
  correctly left untouched via the existing `--skip-story-pass` flag.
  **Verified end-to-end** via headless-Chromium Playwright: real
  screenshots of both golden-boot cards (Man City's Haaland, Bournemouth's
  Evanilson) showing the score, scorecard, and full 38-game campaign
  table together; the champion-shaped final table showing real W/D/L
  numbers that sum correctly (e.g. Arsenal 24W/7D/7L); a synthetic click
  onto a real screen coordinate confirming the whole-map pause
  (~600ms hold at the untouched camera extent, sampled frame-by-frame)
  and the deeper story-zoom (camera landing at a genuine 6x6-world-unit
  window, screenshotted showing the highlighted cell filling roughly a
  sixth of the canvas); and the prior round's regression checks (tap-to-
  ID, canvas corners, back-button spacing/text) all re-run clean against
  the new code. One incidental fix along the way: the desktop campaign
  table's xG column (76px) turned out to be a few px too narrow at the
  larger 13px desktop font (visually confirmed via a high-DPI crop
  showing a genuine ellipsis, despite `scrollWidth`/`clientWidth`
  reporting an exact, non-overflowing fit -- a sub-pixel rounding quirk,
  not a measurement bug) -- widened to 86px, matching-or-exceeding the
  mobile breakpoint's already-correct 80px rather than being narrower
  than it.

  **2026-08-30, done — two new scroll-driven sections: "re-roll one game"
  and "simulated season", both with placeholder headings/copy for the
  user to fill in.** User request: pick a match and, if shot-position
  data is available, visualise it on a pitch as the reader scrolls, each
  shot sized proportional to xG, flashing on its result then settling
  into a faded, still-visible state, with an accompanying log (minute,
  player, xG, real result, sim result) and a scoreboard; separately, a
  380-game simulated season revealed 10 games (one gameweek) at a time
  with an updating league table alongside, with the existing treemap
  moved to sit underneath it. Four clarifying questions asked up front
  (page order, which match, which season, pacing) — user picked the
  recommended option on all four: intro → game re-roll → season re-roll
  → treemap → (simulator/Leicester unchanged); Man Utd vs Bournemouth for
  the game; a dramatic curated sim left to Claude's pick for the season;
  pure one-gameweek-per-scroll-step pacing.
  **Backend, two new scripts under `simulations/`**: `export_game_reroll.py`
  re-rolls one real match's shots as independent Bernoulli(xG) draws under
  a dedicated fixed seed (`GAME_REROLL_SEED = 20260051`, chosen by
  searching a seed range for a genuinely divergent outcome, not the first
  one tried) — real Man Utd 4-4 Bournemouth, sim 4-5 to Bournemouth.
  Output: `articles/pl-treemap-data/game-reroll-data.json` (39 shots, each
  carrying minute/player/team/x/y/xG/real+sim result/running scoreline).
  `export_season_reroll.py` regenerates one full 1,000,000-sim-universe
  season (sim #41197, the same sim already told as the curated tour's
  `closest_tiebreak` stop — chosen so this section's climax is a title
  race already known to be dramatic, not a fresh unvetted pick) as 38
  real, chronologically-ordered gameweeks with a running table after
  each. Two correctness issues caught before/during building, both by
  deliberate verification rather than assumption: (1) a first draft used
  a truncated `(sim+1, ...)` draw shape, which I initially reasoned was
  safe for a single fixed sim number — recognised on reflection as the
  same `draws_h`/`draws_a` sequential-stream-desync bug this codebase has
  hit before (see the 2026-08-29 entries above), since `draws_a`'s
  starting position in the RNG stream depends on how many values
  `draws_h` consumed, which depends on the requested row count, not on
  which row is kept; fixed by requiring the full `n_sims=1,000,000` shape
  via a new `--n-sims` flag, matching every other script that touches
  `champions.bin`'s universe. (2) Reconstructing "real gameweeks" from
  380 date-sorted results is not just chunking every 10 by date — the
  real fixture list has rearranged/rescheduled matches, so naive chunking
  measurably broke the "every team has played the same number of games at
  each step" property (32 inconsistencies across 10 of 38 rounds,
  confirmed by directly counting games-played per team per round before
  attempting any fix). A first-fit greedy placement got stuck outright
  (a match with no legal round left); a single maximum-weight matching
  per round always found a valid round but scrambled chronology (round
  2 predating round 1, confirmed via printed date ranges). Landed on
  `earliest_perfect_matching`: grow a candidate window from the front of
  the date-sorted remaining list one match at a time, taking the
  smallest window that contains a perfect (10-edge) matching via
  `networkx.max_weight_matching(maxcardinality=True)` — the common case
  (no scheduling conflict) resolves immediately from just the 10
  earliest, and only widens when a real conflict forces it. Verified: 0
  games-played inconsistencies across all 38 rounds × 20 teams; 380
  unique matches; Newcastle's full 38-game campaign log cross-checked
  exactly against the independently-generated `flagged-title-ties.json`
  record (0 mismatches); final table matches that record exactly (the
  final gameweek's table is deliberately overwritten with it rather than
  this script's own simpler points/GD/GF sort, so the title-deciding
  tiebreak is never told two slightly different ways). Runtime ~54s for
  the full regeneration across 380 matches. Output:
  `articles/pl-treemap-data/season-reroll-data.json` (38 gameweeks, 110KB).
  **Frontend, `pl-xg-simulator.html`**: two new `<section>`s inserted
  between the intro and the (already-present) treemap section, each with
  `<!-- HEADING: TBD -->`/`<!-- INTRO COPY: TBD -->` placeholders per this
  file's own authorship convention — no heading or narrative copy
  authored on my own initiative. Both share a new `.reveal-track` CSS
  grid (a sticky visual column beside a plain-flow log/results column)
  and a shared `makeScrollReveal(trackEl, totalSteps, onChange)` helper —
  one scroll-fraction-to-step-count mapping reused for both sections
  rather than two bespoke ones. Game re-roll: an SVG pitch (mirrored
  understat X/Y so home and away shots both plot correctly toward
  opposite ends), shots pre-rendered as circles sized
  `max(3, min(14, 3+sqrt(xG)*13))` and revealed in scroll order via a
  `.revealed` opacity toggle; each reveal also spawns a short-lived
  `.pitch-flash` overlay circle (goal/no-goal coloured,
  `@keyframes pitch-flash-anim` shrinking+fading it out) — deliberately a
  *separate* transient element rather than an animation that "returns" a
  shot's own fill to its resting colour, since a first attempt at the
  latter used `fill:inherit` inside a keyframe block, which resolves
  against the parent element rather than the sibling CSS class rule and
  silently does nothing. A scoreboard and a minute/player/xG/result/result
  log accompany it. Season re-roll: 38 pre-rendered `.season-gw-block`
  divs (opacity-toggled the same way) beside a sticky running table,
  champion-row highlighting gated to the final step only.
  **Verification, iterative and Playwright-driven throughout, not just
  code review**: (1) reveal pacing — the game-reroll track initially came
  out too short for its own 39-shot log (1269px, under one extra
  scroll-screen), read as too fast; fixed by widening `.game-log td`
  padding (5px→13px vertical), re-measured at 1893px (~1.1 extra
  screens), then re-confirmed via a scripted scroll sweep (0/0.15/0.5/
  0.85/1.0 fractions) that shot count, log rows, and both scorelines
  advance together and land on the correct real/sim final scores (4-4 /
  4-5) at the end. (2) mobile scoreboard — an initial 3-column flex row
  let "Manchester United" wrap and crowd the score column at 390px;
  fixed with a dedicated `@media (max-width:640px)` stacked-row layout,
  confirmed via `getBoundingClientRect()` plus a screenshot. (3) a real,
  non-cosmetic bug: `getBoundingClientRect()` reported the game-reroll
  scoreboard's home-team row as on-screen (top:25.6px) while a screenshot
  at the same scroll position showed it hidden — traced to the site's own
  sticky header (`assets/css/style.css`) painting over content that used
  a plain hardcoded `top:20px`/`top:0` instead of the `--header-h`
  custom property `assets/js/nav.js` sets specifically for pages with
  their own sticky elements (the same mechanism due-date.html's sticky
  chart already correctly uses). Fixed
  (`top:calc(var(--header-h, 0px) + 20px)` desktop,
  `top:var(--header-h, 0px)` mobile) and reconciled: re-measured
  `getBoundingClientRect()` (top:0 → top:81) and re-screenshotted both
  the game-reroll and season-reroll sections on desktop and mobile,
  confirming the scoreboard/table now render fully visible below the
  header. (4) final full-page regression: a fresh scroll-through of the
  entire page in both viewports (desktop 1280×900, mobile 390×844)
  listening for page/console errors — zero real errors on either; the
  one console error present on both (`ERR_CONNECTION_RESET` fetching
  Google Fonts) is the same pre-existing, unrelated sandbox network
  block this file's history has already flagged elsewhere (this
  sandbox has no external network access), confirmed by finding its
  source (`assets/css/style.css`'s `@import url('https://fonts.googleapis.com/...')`)
  rather than assumed. Not pushed to `main` — left on
  `claude/pull-latest-main-m1y2cg` per the user's own review-then-merge
  pattern throughout this session; headings and intro copy for both new
  sections are still the user's own to write.
  Merged to `main` on explicit request the same round (fast-forward,
  `4ac26c7..41f50f5`).

  **2026-08-30, later — mobile fixes for both new sections: a shorter
  match, a smaller pitch, a real scroll-pacing bug, and a compact league
  table.** User feedback after seeing the merged sections on a phone: the
  pitch viz "isn't working well on mobile" and should use a match with
  fewer shots; the shot log "needs more space on mobile" with shots
  "appearing faster and more reliably"; the season section's league table
  "takes up too much space" on mobile, to be shrunk-and-simplified or, if
  that's not reasonably possible, dropped there.
  **Fewer shots**: swapped the game-reroll match from Man Utd 4-4
  Bournemouth (39 shots) to Newcastle United 2-3 Liverpool (15 shots --
  genuinely light against the CSV-wide median of 25, not just "a bit
  fewer"), re-seeded (`GAME_REROLL_SEED = 20260011`, found the same way
  as before: searching a seed range for a genuinely divergent outcome --
  this one flips a 2-3 away loss into a 2-1 home win, a real turnaround
  rather than just a different scoreline on the same side winning).
  **Smaller pitch / more room for the log**: root-caused why the sticky
  pitch+scoreboard was crowding the log off-screen on mobile before
  touching anything -- at full column width the pitch alone (600:400
  aspect ratio) plus the scoreboard was eating most of a 390-wide
  viewport's height, since mobile stacks the sticky visual and the list
  in one column rather than side-by-side. Capped `.pitch-chart`'s own
  width (not the whole `.reveal-visual`, which would've cramped the
  scoreboard/legend too) via a `max-width:230px` mobile rule -- shrinks
  the pitch in both dimensions at its fixed aspect ratio without touching
  desktop. Measured before/after rather than eyeballing it: the sticky
  visual's own rendered height dropped from what the original 39-shot/
  full-width pitch would have needed to 339px, leaving 505 of the 844px
  viewport for the log -- confirmed via `offsetHeight` on the real
  rendered page, not estimated.
  **A real scroll-pacing regression, caught before shipping**: swapping
  in a much shorter match (15 shots instead of 39) had an unintended
  side effect on *both* viewports, not just mobile -- `makeScrollReveal`
  paces the reveal across `trackEl.offsetHeight - viewport height`, and
  with a short enough log that "scrollable" distance collapses toward
  zero (measured: mobile dropped to 78px total, and *desktop* -- a
  two-column layout where this hadn't been touched at all -- clamped to
  1px, meaning the entire 15-shot reveal happened within about a single
  pixel of scroll, effectively breaking the scroll-driven reveal
  outright, confirmed by scroll-testing desktop and finding it stuck
  showing 12/15 shots at the scroll position that should have been the
  end). This is exactly the failure mode "shots appearing faster and
  more reliably" pointed at, just more severe than the report suggested
  once actually measured. Fixed with a new `ensureMinScrollable(trackEl,
  minScrollablePx)` helper: tops up `.reveal-list`'s own bottom padding
  by whatever shortfall remains between the track's real rendered height
  and a guaranteed minimum scrollable distance (measured post-layout via
  `requestAnimationFrame`, re-measured on resize), rather than
  hand-tuning row padding per breakpoint to indirectly manufacture enough
  height -- this decouples *scroll pacing* (now a deliberate, guaranteed
  minimum, 420px for the game-reroll track) from *row density* (now a
  free legibility choice), and works identically on both the mobile
  stacked layout and the desktop side-by-side one since it operates on
  the track's actual measured geometry either way. Confirmed empirically,
  not just reasoned about: makeScrollReveal spreads a reveal across the
  *entire* scrollable range regardless of what makes it up, so the padding
  top-up doesn't create a "dead" scroll tail after the log finishes
  revealing -- the last shot lands exactly as the sticky visual releases,
  verified by scroll-sampling both viewports and confirming 15/15 shots
  (and the correct final 2-3/2-1 scoreline) exactly at the track's own
  computed end, not before or after. With pacing decoupled, mobile's log
  row padding was independently retuned for density (13px down to 9px
  vertical, a legibility choice now, not a pacing one).
  **Season table, shrunk and simplified rather than dropped**: tried
  shrinking first (smaller font/padding under the existing single-column
  breakpoint), but a 20-row table can't be shrunk far without becoming
  illegible, and shrinking alone doesn't fix the real problem -- 20 rows
  is 20 rows regardless of font size. Simplified instead: past the same
  860px breakpoint `.reveal-track` itself already switches to a stacked
  single column at (the point the table actually starts competing with
  the results feed for screen space, not an arbitrary phone-only cutoff),
  `renderTable()` now renders a compact top 4 + bottom 3 (7 rows, plus a
  "···" gap row) instead of all 20 -- still the two things that actually
  carry this sim's own drama (the title race decided on a tiebreak, the
  relegation fight), just without the mid-table noise nobody's tracking
  gameweek to gameweek. Driven by a live `matchMedia` query (not a one-off
  width check at load), re-rendering on a resize/rotation across the
  breakpoint so it can't get stuck compact on a resized-wider window or
  vice versa; verified both states directly (mobile: 8 `<tr>`s including
  the ellipsis row at every gameweek sampled, champion row correctly
  appearing only once the final table's own highlighting logic says so;
  desktop: unchanged at a full 20 rows, no ellipsis, confirming the
  breakpoint gate actually gates). Chose shrink-and-simplify over
  dropping the section outright since the compact form still delivers
  the section's own point (an updating table alongside the results) on
  every viewport, just sized to what a phone screen can actually hold.
  **Verified end-to-end**, all fixes together: mobile scroll-sampling
  across both new sections' full tracks (shot/row counts and both
  scorelines advancing correctly; gameweek label, compact table contents,
  and champion highlighting all correct at every sampled point);
  before/after screenshots on mobile showing the shrunk pitch, the now
  clearly-visible log beneath it, and the compact league table; a fresh
  desktop screenshot confirming the shorter match and restored reveal
  still render correctly there too; and a final full-page scroll-through
  regression on both viewports with zero real page errors (the one
  console error present on both, `ERR_CONNECTION_RESET` fetching Google
  Fonts, is the same pre-existing sandbox network block this file's
  history has already flagged repeatedly, confirmed by its source rather
  than assumed). Pushed to `claude/pull-latest-main-m1y2cg`; not merged
  to `main` this round -- back on the review-then-merge pattern until the
  user asks.

  **2026-08-30, later still — season table redesigned as a persistent
  full-height right-hand sidebar on mobile, replacing the top-4/bottom-3
  compact view.** User follow-up, proposing a concrete alternative to the
  compaction above: put the table to the right of the screen, full
  height, with just a 3-letter team code, points, and a "W-D-L" combined
  record. Measured before committing to it rather than assuming it'd
  fit: at that column's width, 20 real rows (small font, tight padding)
  render at 455px tall against 743px of available height below the site
  header on a 390-wide/844-tall viewport -- comfortably under, with no
  overflow -- so there's no need to trim any rows after all; the earlier
  top-4/bottom-3 compaction is gone entirely, replaced by this.
  **Layout**: `#season-reroll-track` gets an ID-scoped override (an ID
  beats the shared `.reveal-track` class the generic mobile stacking
  rule uses, so this doesn't touch the game-reroll section) switching
  mobile from the shared single stacked column back to two columns --
  `1fr` for the results feed, a fixed `112px` for the table -- with
  `order:2`/`order:1` putting the table visually on the right despite
  being first in the DOM. `.reveal-visual`'s `min-height:calc(100vh -
  var(--header-h) - 20px)` is what makes it read as a persistent
  full-height strip rather than a compact card, mirroring the desktop
  layout's own two-column shape rather than inventing a third.
  **Columns**: `TEAM_CODE`, a small new lookup (standard PL 3-letter
  codes -- ARS, MUN, NEW, etc., matching what BBC/Sky/the league itself
  use, with a same-file fallback to the team name's own first 3 letters
  for safety if a team is ever missing from it) plus `W-D-L` formatted as
  a single `w-d-l` string, both rendered only past the same breakpoint
  via a live `matchMedia` check -- same mechanism the earlier compaction
  used, now driving column *format* rather than row count. The `<thead>`
  row (`id="season-table-head"`, new) is rewritten by the same
  `renderHeader(compact)` call rather than hidden/shown via CSS, since
  compact and full modes have a genuinely different column count (3 vs
  7), not just different widths for the same columns.
  **Verified**: real geometry measurement (not assumption) confirming
  all 20 rows render with zero overflow inside the available height;
  scroll-sampled progression through the whole track confirming row
  count stays at 20 throughout, the champion row highlights correctly at
  the final gameweek, and the visible team-code/pts/record values track
  the correct gameweek at each sampled point; before/after screenshots
  at kick-off, mid-season and the final table; desktop confirmed
  completely unaffected (still the original 7-column table, unchanged
  42%/58% grid, via a live `getComputedStyle` check, not just "the CSS
  looks scoped right"); and a fresh full-page regression scroll-through
  on both viewports with zero real page errors (same pre-existing Google
  Fonts sandbox block as every prior round, nothing new). Pushed to
  `claude/pull-latest-main-m1y2cg`; not merged to `main` this round.
  Merged to `main` on explicit request the same round.

  **2026-08-30, later still — a real, confirmed scroll-position bug: the
  mobile browser chrome (address bar) hiding/showing mid-scroll was
  causing the page to involuntarily yank itself around.** User report:
  "the scroll doesn't work properly... it's missing off the top and
  should be much lower" on both new sections. Automated Chromium testing
  (jump-scrolling, sampling reveal counts and sticky-release points
  against scroll position) found nothing -- the underlying reveal math
  was smooth and monotonic throughout, on both viewports. That itself
  was the clue: headless Chromium has no real browser chrome to hide or
  show, so anything caused specifically by that would be invisible to
  it. Reproduced directly instead, using Playwright's `setViewportSize`
  (which fires the same real resize path a mobile address-bar toggle
  does) to simulate one mid-scroll: scrolled to the very bottom of the
  page, shrank the viewport by 64px (a plausible chrome-bar height) with
  no scroll input given -- `scrollY` snapped down by exactly 64px on its
  own. Root cause: `ensureMinScrollable` (added last round, to guarantee
  the game-reroll reveal a minimum scroll distance) recomputed
  `.reveal-list`'s own bottom padding on every `resize` event using the
  live `window.innerHeight` -- and mobile browsers fire `resize`
  continuously as their address bar hides/shows *during* an ordinary
  scroll gesture, with no real layout change behind it. Recomputing that
  padding shrinks or grows the *whole page's* document height, and
  browsers respond to a shrinking document by force-clamping the current
  scroll position -- an involuntary jump mid-scroll, exactly matching
  "missing off the top... should be much lower". **Fix**: a new shared
  `stableViewportHeight()` only trusts a new `window.innerHeight`
  reading when the width also changed (address-bar toggling only ever
  touches height) or the height moved by more than a chrome-bar-sized
  amount (150px) -- filtering out the toggle while still tracking a
  genuine orientation flip or desktop window resize. Both
  `makeScrollReveal` (previously read `window.innerHeight` live on every
  scroll tick, a smaller version of the same problem) and
  `ensureMinScrollable` now read this instead. `ensureMinScrollable`
  also lost a second, related anti-pattern while in there: it used to
  reset padding-bottom to `0px` before every recompute to get an
  unpadded height reading, which briefly shrinks the document on *every*
  resize by itself, even a trusted one -- now the unpadded base height
  is measured once, on the very first call, and cached, so a later
  recompute never needs to zero anything out first. Also swapped the
  season sidebar's `min-height:calc(100vh - ...)` for a redeclared
  `100svh` version (kept the `100vh` line first as a fallback for
  browsers that don't recognise the unit) -- `svh` ("small viewport
  height") always assumes the browser chrome is visible, so it can't
  grow/shrink from chrome toggling the way plain `vh` does; confirmed
  this specific rule wasn't actually the trigger for the scroll-clamp
  bug (the sidebar was never the taller of its track's two columns, so
  its own height fluctuating didn't move the *track's* height), but it's
  the same class of problem and the standard purpose-built fix, cheap to
  apply regardless. **Verified the fix, not just the theory**: re-ran
  the exact repro (bottom-of-page, then a 64px viewport shrink) --
  `scrollY` no longer moves at all (was -64px, now 0px); confirmed a
  *genuine* resize (a real orientation flip, width and height swapped)
  still recalibrates correctly, so the fix suppresses the toggle without
  breaking real resize handling; and reconfirmed the full existing
  verification suite (scroll-sampled progression on both sections/both
  viewports, sticky-release timing, full-page regression) all still
  pass. **One small residual, disclosed rather than chased**: a
  much smaller (~40px) document-height fluctuation on resize remains,
  traced to `.intro`/`section`'s own `vh`-based padding and margins --
  pre-existing site-wide spacing conventions that predate this session
  entirely, used throughout every section on the page, not something
  introduced by the new sections. Confirmed this residual causes no
  scroll-clamp on its own (scrollY delta measured at exactly 0 in the
  same repro) and can nudge a reveal count by at most one step in an
  edge case -- real, but far smaller and more diffuse than the
  concentrated jump that was actually reported, and fixing it would mean
  changing a site-wide layout convention out of scope for this round;
  left as-is. Pushed to `claude/pull-latest-main-m1y2cg`.
  Merged to `main` on explicit request the same round.

  **2026-08-30, later still — the actual bug: a site-wide `--header-h`
  race, not the mobile-toolbar fix from the previous entry.** User
  report after the merge above: "looks like that didn't work." Asked a
  clarifying question this time before another blind round of Chromium
  probing -- iPhone Safari, both new sections, "same way" -- since the
  previous round's fix was for a Chromium-reproducible mechanism
  (address-bar-resize scroll clamp) that might simply not be what a real
  iPhone does at all, and a second guess without new information would
  have been exactly that: a guess. With "both sections, same way"
  confirmed, the common ground between them stopped being anything
  scroll-dynamics-related (game-reroll and season-reroll don't share
  `ensureMinScrollable` or the CSS Grid `order` trick) and became the one
  thing every sticky element on the page actually depends on:
  `var(--header-h, 0px)`. Reproduced directly: forcing `--header-h` to
  `0px` on an already-loaded page produces the *exact* reported symptom
  on both sections -- the scoreboard/pitch card and the season table both
  render with their top portion sliced off, hidden behind the site's own
  sticky header (`z-index:10` vs. the cards' `z-index:2`), the rest of
  each card sitting where a reader would expect it "much lower" than
  where it actually shows. **Root cause**: `nav.js` is deliberately the
  very last thing to run on every page (so it doesn't block anything
  above it from parsing) -- it injects the header and only *then* sets
  `--header-h` via `element.style.setProperty(...)`. Every
  `position:sticky` element elsewhere on the page that reads
  `var(--header-h, 0px)` -- both new sections here, and due-date.html's
  own sticky chart -- gets its *first* layout pass before that property
  has ever been set, falling back to the literal `0px` in that fallback
  clause. Chromium correctly re-triggers the sticky offset once the
  property is set moments later (confirmed -- this is exactly why every
  previous Chromium-based check here, including the sticky-release
  sampling two entries back, never caught it); Safari has a real,
  documented history of *not* reliably redoing that recalculation for a
  sticky element once its first layout has already happened, leaving it
  stuck at the stale `0px` offset for good, with nothing to force a
  second look. **Fix**: `assets/css/style.css` gains a real, *measured*
  (not guessed) static default for `--header-h` on `:root` --
  `107px` above the site's existing 600px nav breakpoint, `81px` at or
  below it, both read directly off `.site-header`'s actual rendered
  height at each width via Playwright before writing the numbers down.
  `nav.js`'s inline `element.style.setProperty(...)` still wins over this
  (inline styles always beat stylesheet rules), so nothing changes for a
  browser that *does* pick up the later update -- this only changes what
  every sticky element gets *before* nav.js has run, and what it's stuck
  with forever on a browser that never revisits it. Fixing this in the
  shared stylesheet (not just this article) means due-date.html's own
  sticky chart -- built on the identical pattern, and never reported
  broken, but never confirmed working on a real iPhone either -- is
  covered by the same fix rather than leaving a second, unreported
  instance of the same bug in place. **Verified two ways**: the original
  repro (forcing `--header-h` to `0px` after load) is no longer the
  relevant failure mode to chase, since the fix targets *before nav.js
  runs at all* -- so verified that specific window instead, by aborting
  the request for `nav.js` outright (the worst case: the JS-based
  measurement never runs, ever) and confirming `--header-h` still
  resolves to `81px` from the CSS default alone, with the game-reroll
  card rendering fully intact, nothing clipped. Then confirmed the
  normal path (`nav.js` running as usual) is pixel-identical to before on
  both sections/both viewports and on due-date.html specifically (its
  own `--header-h` reads and screenshot unchanged, zero page errors) --
  this is a purely additive fallback, not a behaviour change for the
  common case. Full existing verification suite (scroll-sampled
  progression, sticky-release timing, row counts, full-page regression)
  re-run clean on top of it. Considered and deliberately left alone: the
  season sidebar's CSS Grid `order:1`/`order:2` trick, the one genuinely
  unprecedented pattern introduced this session (nothing else on the
  site reorders a sticky grid item this way, and WebKit does have its
  own separate history of sticky+order quirks) -- but it doesn't explain
  the *specific* symptom actually reproduced (a content clip under the
  header, not a layout scramble), removing it would mean un-mirroring
  desktop's matching left/right convention across both new sections too,
  and there's now a confirmed, precisely-targeted explanation that
  doesn't need it. Flagging it here rather than touching it speculatively
  on top of an already-identified fix. Pushed to
  `claude/pull-latest-main-m1y2cg`.
  Merged to `main` on explicit request the same round.

  **2026-08-30, later still — replaced the hand-rolled scroll-fraction
  reveal with IntersectionObserver, after the --header-h fix genuinely
  didn't fix it either.** The user tested the merge above on their own
  iPhone and sent real screenshots -- the header-clip bug was gone (the
  fix from the previous entry did work, confirmed directly), but the
  reveal itself was still broken: rows appearing "only a tiny bit below
  the chart/top of screen" instead of spread across a real scroll,
  matching what the screenshots showed -- a card followed almost
  immediately by a large blank gap, not a naturally long, readable list.
  **Diagnosis**: `makeScrollReveal` computed a reveal fraction from
  `trackEl.offsetHeight - viewportHeight`, and `ensureMinScrollable`
  manufactured a guaranteed minimum for that by padding `.reveal-list`.
  Both depend on getting real-device viewport-height arithmetic exactly
  right -- and across three straight rounds, each specific mechanism
  that turned out to be wrong (a mobile-chrome-resize scroll-clamp bug,
  a --header-h race) got found and fixed, and the *next* round still
  found a *different* symptom in the same family. That pattern -- not
  any single remaining bug -- was the actual signal: hand-rolled
  viewport-height math driving a scroll reveal is fragile on real
  mobile Safari in ways that keep surfacing new failure modes, and
  chasing the Nth one wasn't going to be more reliable than the first
  two weren't. **Fix**: replaced both `makeScrollReveal` and
  `ensureMinScrollable` outright with `revealOnScroll`, built on
  `IntersectionObserver` -- the browser's own native primitive for
  "has this element scrolled into view", which needs no viewport-height
  arithmetic in JS at all and is exactly the semantic the user asked
  for ("rows coming from the bottom of the screen"): each row/gameweek
  block is observed individually and reveals as it enters the viewport,
  not via a fraction computed against the whole track. Deliberately
  one-directional (revealed items stay revealed even scrolling back up)
  -- a small, deliberate simplification of the old symmetric
  reveal/un-reveal, and a common convention for this kind of effect,
  traded for removing an entire class of bug rather than chasing it
  further. Both call sites simplified to match: `revealShot(i)` /
  `revealGameweek(i)` update score/table/label directly from that one
  item's own data, no `count`/`revealed` bookkeeping needed. Also
  deleted the two CSS comments that referenced `ensureMinScrollable`,
  now stale. **Verified**: scroll-sampled progression on both sections,
  both viewports, confirming monotonic reveal counts and correct
  final states (15/15 shots, 2-3/2-1 final score; 38/38 gameweeks,
  champion row correct) that hold even scrolling past the section's
  end; screenshots at several points on both viewports showing rows
  revealing at sensible positions with no large blank gaps; the
  existing season-sidebar and full-page regression suites re-run
  clean, zero real page errors. Cannot verify the *specific* real-iPhone
  behaviour this was chasing without a real device or WebKit (still
  unavailable in this sandbox), but the whole point of moving to
  IntersectionObserver is that this class of bug shouldn't depend on
  getting that verification right any more -- it's a mature, w3c-spec'd,
  broadly-supported API doing the "did this scroll into view" check
  itself, not a hand-rolled approximation of it. Pushed to
  `claude/pull-latest-main-m1y2cg`.
  Merged to `main` on explicit request the same round.

  **2026-08-30, later still — sequenced the reveal so the sticky visual
  reaches the top of the screen before any row/gameweek starts entering
  from the bottom.** User feedback on the IntersectionObserver rewrite:
  the sticky pitch/table needs to reach the top of the screen before the
  scrolling content starts entering from the bottom, rather than both
  happening at once as the section first scrolls into view. Root cause:
  the sticky wrap sits at the very top of its track in both sections
  (the game-reroll pitch is literally the track's first child; the
  season table shares the same grid row as the results feed, starting
  at the same top edge), so `revealOnScroll`'s per-item observers,
  armed the instant each section's script ran, could already find early
  items intersecting near the bottom of a tall viewport before the
  sticky card had actually finished sliding up into its pinned
  position. **Fix**: a new `afterStickyPinned(trackEl, callback)` gate
  -- a one-time check (`trackEl.getBoundingClientRect().top <=` the
  site header's own live `offsetHeight`), armed via the same
  scroll/resize/rAF pattern as before but checking a plain boolean, not
  a fraction or shortfall -- delays calling `revealOnScroll` until the
  track has scrolled far enough that its sticky child would already be
  pinned. Deliberately reads the header's real DOM height directly
  rather than going through `--header-h`, one less indirection to ever
  be stale. **Verification hit a real false alarm worth recording**: an
  early test scanned the game section in fine detail up to a y just
  past the season section's own pin point, then jumped *back* to start
  the season scan from its nominal boundary -- a backward jump no real
  scroll gesture makes, which let season's (already correctly, forward-
  armed) observer show revealed items when re-queried at that earlier
  y, reading as a gate failure that wasn't one. Confirmed genuinely
  fixed two ways: instrumented the real `IntersectionObserver.observe`
  to log the exact `scrollY` each section's reveal actually arms at
  (season: 2320, matching its measured pin point of 2320 exactly), and
  a corrected single-pass monotonic scan (each phase's start clamped to
  where the previous one actually left off, never re-visiting an
  earlier scrollY) showing `firstRevealAt === pinnedAt` exactly for
  both sections on both viewports, zero early reveals. Full existing
  regression suite re-run clean on top of it. Pushed to
  `claude/pull-latest-main-m1y2cg`.
  Merged to `main` on explicit request the same round.

  **2026-08-30, later still — the actual remaining gap: a batch of items
  revealing all at once the instant the card pins, not one at a time
  from a blank start.** User report after testing the sequencing fix
  above: the table should stay blank until the pitch (or, for the
  second section, the league table) reaches the top, *then* entries
  should enter from the bottom on scroll -- implying the previous round
  hadn't actually delivered that. It hadn't, fully: `afterStickyPinned`
  correctly stopped anything revealing *before* pin, verified rigorously
  last round, but nobody had checked how much reveals in the same instant
  pin happens. Measured directly: right at the pin moment, 6 of 15 shots
  and 2 of 38 gameweeks were already revealed -- a batch, not a blank
  start. **Root cause**: the list sits either right after the sticky
  card in document flow (mobile's stacked game-reroll layout) or beside
  it in the very same grid row (every other layout/section combination)
  -- either way, a chunk of the list's own natural content is already
  sitting in whatever screen space the card doesn't cover the instant
  the card reaches its pinned position, since IntersectionObserver
  (armed the moment `afterStickyPinned`'s callback fires) evaluates
  against *current* geometry, and several rows already qualify at that
  first check. **Fix**: a new `padUntilPinnedIsBlank(trackEl)`, called
  alongside `afterStickyPinned`, pads `.reveal-list`'s own top by
  exactly the shortfall needed to push its first item below the fold at
  the pin moment -- computed from the list's fixed offset from the
  track's own top (measured once; doesn't depend on scroll position),
  subtracted from the viewport height. Computed once on load and never
  touched again on resize, deliberately -- an earlier version of this
  reveal mechanism reacted to every resize (mobile address-bar toggles
  included) and that caused a real, confirmed scroll-position bug two
  rounds back; this doesn't repeat it. **Verified**: re-measured the
  exact same "how much reveals right at the pin instant" check that
  caught the bug -- 0 shots and 0 gameweeks now, on both viewports;
  confirmed the reveal still progresses correctly and monotonically to
  a full, correct final state afterward (15/15 shots, 2-3/2-1 score;
  38/38 gameweeks, champion row correct); screenshots at the pin moment
  on both sections/both viewports showing a genuinely blank list beside
  a fully-rendered card, and at a bit further scroll showing exactly a
  couple of items having entered with plenty of blank space still below
  -- the effect asked for; full regression suite re-run clean. Pushed
  to `claude/pull-latest-main-m1y2cg`.
