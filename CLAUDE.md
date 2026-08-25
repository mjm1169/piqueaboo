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

  **2026-08-25, in progress — genuinely-1,000,000-cell zoomable treemap**
  (see `/root/.claude/plans/purring-finding-badger.md` for the full plan,
  agreed with the user): the "zoom through the treemap" idea above is being
  built out as a guided-flythrough zoom into real, individually-addressable
  simulation cells, backed by a real three-tier save policy on the
  1,000,000-sim run (who-won by default; full season table when the
  champion is an "unexpected winner" — real position outside the top half;
  full match detail when a game hits 15+ total goals or a player scores
  6+, the latter capped to one flagged instance per real fixture).
  **Part 1 (backend) is done and checked in**: `simulations/export_treemap_data.py`'s
  big pass now writes `articles/pl-treemap-data/flagged-champions.json`
  (2,002 sims) and `flagged-games.json` (1,023 sims: 987 high-scoring, 36
  deduped 6+-goal hauls) alongside the existing `champions.bin` /
  `treemap-data.json`. Every flagged record carries a real global `sim`
  index (0..999,999) into `champions.bin`. **Part 2 (frontend) is not
  started**: `pl-xg-simulator.html`'s treemap script still only draws the
  ~20 aggregate team blocks from `treemap-data.json`/`champions.bin` — it
  doesn't yet read the two new flagged-data files, has no per-team zoomed-in
  grid renderer, and no guided-flythrough camera/UI. That's the next piece.
