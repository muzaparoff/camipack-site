/* Camipack — language memory.

   The site ships one folder per language, so switching language means walking to the
   same page in another folder. This script does the two things the static markup
   cannot do on its own:

     1. Remembers the reader's choice in localStorage, so it survives navigating to
        the next page and coming back tomorrow — until they choose differently.
     2. Points every item in the language menu at the page the reader is actually on.
        The markup ships them all aimed at how-it-works.html, so switching language
        from anywhere else quietly moved you to a different page as well.

   Nothing here is required to read the site. With scripting off the menu behaves
   exactly as it did before — the same bargain the menu's <details> markup makes.

   One localStorage key, no cookies, nothing leaves the browser. */
(function () {
  'use strict';

  var KEY = 'camipack-lang';

  /* Language code -> folder under the site root. English is the root itself. */
  var FOLDER = { en: '', de: 'de', es: 'es', fr: 'fr', pl: 'pl', pt: 'pt', ru: 'ru' };

  /* The pages that exist inside every language folder — all of them, now that
     index.html and privacy-policy.html are translated too. Anything not listed here
     is English-only, and a reader asking for it in another language lands on that
     language's how-it-works page rather than a 404. */
  var TRANSLATED = [
    'index.html', 'how-it-works.html', 'support.html', 'updates.html',
    'privacy-policy.html',
    'tripit-alternative.html', 'tripsy-alternative.html', 'wanderlog-alternative.html'
  ];
  var FALLBACK = 'how-it-works.html';

  /* The menu says pt-PT; the folder is called pt. */
  function norm(code) {
    return String(code || '').toLowerCase().split('-')[0];
  }

  /* Which language and which page we are looking at, and how to climb to the root. */
  function here() {
    var parts = location.pathname.split('/').filter(Boolean);
    var slug = location.pathname.slice(-1) === '/'
      ? 'index.html'
      : (parts.pop() || 'index.html');
    var folder = parts.length ? parts[parts.length - 1] : '';
    var lang = 'en';
    for (var code in FOLDER) {
      if (FOLDER[code] && FOLDER[code] === folder) { lang = code; }
    }
    return { lang: lang, slug: slug, up: lang === 'en' ? '' : '../' };
  }

  /* Where `slug` lives in `lang`, written relative to the page we are on. */
  function target(lang, slug, up) {
    if (!(lang in FOLDER)) { return null; }
    if (lang !== 'en' && TRANSLATED.indexOf(slug) === -1) { slug = FALLBACK; }
    var folder = FOLDER[lang];
    return up + (folder ? folder + '/' : '') + slug;
  }

  function remembered() {
    try { return localStorage.getItem(KEY); } catch (e) { return null; }
  }

  var page = here();

  /* 1. Honour a remembered language before anything paints, so there is no flash of
        the wrong one. `replace` keeps the page we are leaving out of the back
        history — otherwise Back would land here and bounce straight forward again.
        The fallback above guarantees we always arrive in the remembered language,
        which is what stops this redirecting a second time. */
  var want = remembered();
  if (want && want !== page.lang && want in FOLDER) {
    var to = target(want, page.slug, page.up);
    if (to) { location.replace(to); return; }
  }

  /* 2. Aim the menu at this page, and remember whatever the reader picks. */
  document.addEventListener('DOMContentLoaded', function () {
    var menu = document.querySelector('.langs ul');
    if (!menu) { return; }

    var links = menu.querySelectorAll('a[hreflang]');
    for (var i = 0; i < links.length; i++) {
      var href = target(norm(links[i].getAttribute('hreflang')), page.slug, page.up);
      if (href) { links[i].setAttribute('href', href); }
    }

    /* Delegated, so it still works on the flag <span> inside each link. */
    menu.addEventListener('click', function (e) {
      var a = e.target && e.target.closest ? e.target.closest('a[hreflang]') : null;
      if (!a) { return; }
      try { localStorage.setItem(KEY, norm(a.getAttribute('hreflang'))); } catch (err) {}
    });
  });
})();
