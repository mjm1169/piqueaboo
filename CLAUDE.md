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

  **2026-08-25, in progress — real tie-breaks, full scorecards/campaigns,
  "Other" grouping** (see `/root/.claude/plans/purring-finding-badger.md`
  for the full plan): replaces the simplified GD→GF→coin-toss tie-break
  with the real Premier League chain (GD, GF, head-to-head points,
  head-to-head away goals, coin flip standing in for a play-off), flags a
  title decided at head-to-head-or-later as its own story type, adds full
  ordered scorecards (player/minute/penalty) to flagged games, and full
  38-game campaign logs (opponent, H/A, sim score, xG score) to flagged
  champions. **Part 1 (backend) is done and checked in**:
  `simulations/simulate_season.py` gained `build_h2h_fixture_index()` /
  `resolve_tied_group()` (the real tie-break chain, reused everywhere
  match-level detail is available) and per-shot minute/penalty arrays in
  `build_match_index()`. `simulations/export_treemap_data.py`'s big pass is
  now two sweeps: sweep 1 (unchanged in spirit, now seeds each match's
  draws independently via `SeedSequence([seed, match_index])` so sweep 2
  can regenerate any match's results bit-for-bit identically without
  replaying the whole match list) detects title-level ties (~37 on this
  run) and captures full scorecards on flagged games; sweep 2 resolves
  those pending ties via head-to-head and builds a 38-game campaign log for
  every flagged champion. New output: `flagged-title-ties.json`. The small
  story batch and the article's own `sim_leicester_2015_16.json` generator
  now use the same real tie-break chain too (cheap there — full match
  detail is already retained for every sim at that scale). Full
  1,000,000-sim regeneration verified end-to-end: 1,985 flagged champions,
  987 flagged games, 37 flagged title ties, all cross-checked by hand
  (campaign W/D/L/GF/GA sums match each champion's final table exactly,
  scorecards match the raw shot data's minutes/penalty flags exactly, all
  7 title-tie resolutions verified by hand at dry-run scale before the
  full run). Total combined data payload is now ~16MB (mostly
  `flagged-champions.json`'s campaign logs) — up from ~15MB before, still a
  one-time fetch. **Part 2 (frontend) is not started**: none of this new
  data is read by `pl-xg-simulator.html` yet — no scorecard/campaign
  display, no title-tie story type, no "Other" grouping, and the mobile
  tween-speed complaint (too fast to track) is unaddressed.
