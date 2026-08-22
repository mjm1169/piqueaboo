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

- `articles/pl-xg-simulator.html` — the current prose and visual treatments
  (gauge spinners, scoreline/trophy cards, movers panel, bar charts, all
  section copy) were drafted by Claude before the rule above was made
  explicit. The underlying data pipeline (`simulations/`) and client-side
  simulator logic are solid and can stay — but the article's writing and
  visual design should be redone with the user next time this is picked up.
