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
  paragraph also still has a literal `20xx/xx` season placeholder. The
  user separately mentioned wanting a "zoom through the treemap"
  interaction built for the highlights callout — not yet implemented.
  `index.html`'s teaser card for this article is still placeholder copy
  and wasn't touched by this pass.
