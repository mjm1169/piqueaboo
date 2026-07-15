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

Push to the `main` branch. GitHub Pages (repo Settings → Pages) is configured
to deploy from branch `main`, folder `/ (root)`. Custom domain (piqueaboo.uk)
is set both in that Pages settings page and via the `CNAME` file in this repo
— GitHub uses the `CNAME` file to know which repo should handle requests for
the domain once DNS points at it.

The domain is also verified at the GitHub **account** level (account Settings
→ Pages → verified domains), via a one-time TXT record challenge. This locks
`piqueaboo.uk` to this GitHub account permanently, so no other repo (this
account's or anyone else's) can claim it as a custom domain — even if this
site is ever taken down while DNS still points at GitHub.

## DNS (Porkbun, Cloudflare-hosted)

Four `A` records on the root (`piqueaboo.uk`), pointing at GitHub Pages'
shared IPs:

```
185.199.108.153
185.199.109.153
185.199.110.153
185.199.111.153
```

Plus a `CNAME` record so `www.piqueaboo.uk` also resolves:

```
www.piqueaboo.uk  →  mjm1169.github.io.
```

Porkbun's default parking records (an `ALIAS` on the root and a wildcard
`CNAME` pointing at `pixie.porkbun.com`) were removed to make room for these
— if the domain ever stops resolving to the site, check that a default
parking record hasn't been re-added and that the A records above are still
present.
