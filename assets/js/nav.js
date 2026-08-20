// Piqueaboo — shared site header/footer
// Injected on every page so nav only needs to be maintained in one place.

function renderNav(activePage) {
  const isArticle = document.body.classList.contains('article-page');
  const prefix = isArticle ? '../' : '';

  const header = document.createElement('header');
  header.className = 'site-header';
  header.innerHTML = `
    <div class="nav-inner">
      <a href="${prefix}index.html" class="site-title">
        Piqueaboo
        <span class="site-tagline">data, revealed</span>
      </a>
      <nav class="nav-links">
        <a href="${prefix}index.html" class="${activePage === 'articles' ? 'active' : ''}">Articles</a>
        <a href="${prefix}about.html" class="${activePage === 'about' ? 'active' : ''}">About</a>
      </nav>
    </div>
  `;
  document.body.insertBefore(header, document.body.firstChild);

  // Expose the sticky header's rendered height as a CSS var so pages with
  // their own sticky/fixed elements (e.g. the due-date report's sticky
  // chart column) can offset below it instead of being covered by it.
  const setHeaderHeightVar = () => {
    document.documentElement.style.setProperty('--header-h', header.offsetHeight + 'px');
  };
  setHeaderHeightVar();
  window.addEventListener('resize', setHeaderHeightVar);

  const footer = document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = `
    <p>Piqueaboo &mdash; data, revealed.</p>
    <img src="${prefix}assets/logos/piqueaboo-logo.svg" alt="Piqueaboo" class="footer-logo">
  `;
  document.body.appendChild(footer);
}
