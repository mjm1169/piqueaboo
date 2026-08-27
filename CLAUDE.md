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
  block in this sandbox (not caused by this change). Not yet pushed to
  `main` -- left on `claude/pl-xg-article-commentary-cnrfz3` as with the
  rest of this session's work, pending an explicit merge request.
