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

  const footer = document.createElement('footer');
  footer.className = 'site-footer';
  footer.innerHTML = `<p>Piqueaboo &mdash; data, revealed.</p>`;
  document.body.appendChild(footer);
}
