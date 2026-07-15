# Piqueaboo

Personal site — visuals and stories from public data. Hand-built HTML/CSS/JS, D3 for charts, scroll-driven interactions where relevant. Hosted on GitHub Pages, domain via Porkbun.

## Structure

```
index.html          — homepage / article listing ("Articles" tab)
about.html           — About page
CNAME                — custom domain config for GitHub Pages
assets/css/style.css — shared stylesheet (design system tokens)
assets/js/nav.js     — shared header/footer, injected on every page
articles/            — one HTML file per article
articles/_template.html — starting point for new articles
```

## Adding a new article

1. Copy `articles/_template.html` to `articles/your-article-slug.html`
2. Build the piece
3. Add a card for it on `index.html` linking to `articles/your-article-slug.html`

## Local preview

No build step — just open the HTML files directly in a browser, or run a
simple local server from the project root:

```
python3 -m http.server 8000
```

Then visit `http://localhost:8000`.

## Deploying

Push to the `main` branch. GitHub Pages is configured to serve from root.
Custom domain (piqueaboo.uk) is set via the CNAME file plus DNS records at
Porkbun (see below) — should already be configured once initially set up.

## DNS (Porkbun)

A records pointing to GitHub Pages IPs, or a CNAME depending on setup —
configured once when the domain was first connected. Check Porkbun DNS
settings if the site ever needs re-pointing.
