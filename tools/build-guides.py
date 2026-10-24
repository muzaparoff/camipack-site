#!/usr/bin/env python3
"""Builds camipack.com/guides from the app's own Help.

    python3 tools/build-guides.py [--updated "24 Oct 2026"]

Reads tools/guides.json (written by the app's -exportGuides seam; see
Scripts/capture-guides.sh in the app repo) and tools/guides-meta.json (kept by
hand: minutes, the featured guide, the orange tap highlights, placeholders).
Writes docs/guides/index.html and docs/guides/<slug>.html, adds the pages to
docs/sitemap.xml and a "Guides" item to every English page's header.

Step text is the app's Help text, word for word, so the app and the site never
disagree; nothing here rewrites it. Screenshots are docs/guides/img/<slug>-<n>.jpg
from the capture run; until a step has one, its placeholder (an older image from
docs/img) stands in, and the build lists every step still on one.

English only for now. Translated guides follow once the app's Help
translations are exported the same way (-AppleLanguages per language).
Standard library only.
"""
import argparse
import datetime
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "guides"
SITE = "https://camipack.com"
STORE = "https://apps.apple.com/app/apple-store/id6798912287?pt=128092100&amp;ct=website-guides&amp;mt=8"
LANGS = [("ru", "ru", "ru", "🇷🇺", "Русский"), ("de", "de", "de", "🇩🇪", "Deutsch"),
         ("es", "es", "es", "🇪🇸", "Español"), ("fr", "fr", "fr", "🇫🇷", "Français"),
         ("pl", "pl", "pl", "🇵🇱", "Polski"), ("pt", "pt-PT", "pt-PT", "🇵🇹", "Português"),
         ("uk", "uk", "uk", "🇺🇦", "Українська")]
NAV = [("how-it-works.html", "How it works"), ("guides/index.html", "Guides"),
       ("updates.html", "What's new"), ("index.html#pricing", "Pricing"),
       ("support.html", "Support"), ("privacy-policy.html", "Privacy")]

e = html.escape


def header(up, current):
    """The site header, as every page writes it: the page you are on is left
    out of the nav. Guide pages are English-only, so the language menu sends
    other languages to their how-it-works page — what lang.js does for any
    untranslated page. lang.js itself is not loaded: it assumes a page sits at
    the root or one language folder down, and guides/ is neither."""
    links = "".join(f'<a href="{up}{href}">{label}</a>' for href, label in NAV if href != current)
    langs = "".join(
        f'<li><a href="{up}{folder}/how-it-works.html" hreflang="{hl}" lang="{lang}">'
        f'<span class="fl" aria-hidden="true">{flag}</span>{name}</a></li>'
        for folder, hl, lang, flag, name in LANGS)
    return f'''  <header class="site">
    <a href="{up}index.html">
      <img src="{up}img/app-icon.png" alt="Camipack">
      <span class="name">Camipack</span>
    </a>
    <nav><div class="menu-panel">{links}</div><details class="langs" name="camipack-hdr"><summary aria-label="Change language"><span class="fl" aria-hidden="true">🌐</span><span class="cur">English</span></summary><ul><li><span class="on" aria-current="true" lang="en"><span class="fl" aria-hidden="true">🌐</span>English</span></li>{langs}</ul></details><details class="menu" name="camipack-hdr"><summary aria-label="Menu"><span class="bars" aria-hidden="true"></span></summary></details></nav>
  </header>'''


def footer(up):
    return f'''  <footer class="site">
    <nav class="social" aria-label="Camipack on social media">
      <span class="lbl">Follow Camipack</span>
      <a href="https://www.youtube.com/@Camipack" target="_blank" rel="noopener me" aria-label="Camipack on YouTube (opens in a new tab)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="2.5" y="5.5" width="19" height="13" rx="4"/><path d="M10 9.2v5.6l4.8-2.8z" fill="currentColor" stroke="none"/></svg>YouTube</a>
      <a href="https://www.instagram.com/camipackapp/" target="_blank" rel="noopener me" aria-label="Camipack on Instagram (opens in a new tab)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.2" cy="6.8" r="1" fill="currentColor" stroke="none"/></svg>Instagram</a>
      <a href="https://www.tiktok.com/@camipack" target="_blank" rel="noopener me" aria-label="Camipack on TikTok (opens in a new tab)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M13.5 3.5v11.2a3.6 3.6 0 1 1-3.6-3.6"/><path d="M13.5 3.5c.4 2.6 2.3 4.4 5 4.6"/></svg>TikTok</a>
    </nav>
    <span>© 2026 Camipack</span>
    <a href="https://apps.apple.com/app/apple-store/id6798912287?pt=128092100&amp;ct=website-footer&amp;mt=8">App Store</a>
    <a href="{up}index.html">Home</a>
    <a href="{up}how-it-works.html">How it works</a>
    <a href="{up}updates.html">Release notes</a>
    <a href="{up}privacy-policy.html">Privacy policy</a>
    <a href="{up}terms-of-service.html">Terms of Service</a>
  </footer>'''


# Page styles on top of style.css, in its tokens, like how-it-works.html keeps
# its own. The highlight is orange in both themes: it marks a tap, not a brand.
STYLE = '''<style>
  [hidden] { display: none !important; }
  :root { --tap: #f07a1a; --tap-soft: rgba(240, 122, 26, 0.16); }
  @media (prefers-color-scheme: dark) { :root { --tap: #ff9a45; --tap-soft: rgba(255, 154, 69, 0.18); }
    .gstep .phone { box-shadow: 0 0 0 1px var(--line), 0 16px 40px rgba(0,0,0,0.25); } }
  .search { display: flex; align-items: center; gap: 10px; background: var(--card);
    border: 1px solid var(--line); border-radius: 12px; padding: 10px 14px; margin: 22px 0 18px; }
  .search:focus-within { border-color: var(--green); }
  .search svg { width: 18px; height: 18px; flex: none; color: var(--ink-2); }
  .search input { flex: 1; min-width: 0; border: 0; outline: 0; background: transparent;
    color: var(--ink); font: inherit; font-size: 16px; }
  .guide-card { display: block; text-decoration: none; color: inherit; }
  .guide-card:hover h3 { color: var(--green); }
  .guide-card:focus-visible { outline: 2px solid var(--green); outline-offset: 2px; }
  .guide-card .meta { font-size: 13px; color: var(--ink-2); margin-top: 6px; }
  .featured { display: flex; gap: 16px; align-items: center; padding: 22px;
    background: var(--green-soft); box-shadow: none; margin-bottom: 14px; }
  .featured .icon { font-size: 28px; margin: 0; color: var(--green); }
  .featured h3 { font-size: 20px; margin: 0 0 4px; }
  .empty { color: var(--ink-2); font-size: 15px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 18px; }
  .chip { font-size: 13px; font-weight: 700; color: var(--ink-2); background: var(--card);
    border: 1px solid var(--line); border-radius: 999px; padding: 4px 11px; }
  .open-app { display: inline-block; background: var(--green); color: var(--page);
    border-radius: 10px; padding: 10px 18px; text-decoration: none; font-weight: 700; font-size: 15px; }
  .open-note { font-size: 13.5px; color: var(--ink-2); margin: 8px 0 0; }
  .gsteps { list-style: none; margin: 32px 0 0; padding: 0; }
  .gstep { display: grid; grid-template-columns: 1fr 260px; gap: 28px; align-items: start;
    padding: 26px 0; border-top: 1px solid var(--line); }
  .gstep.noshot { grid-template-columns: 1fr; }
  .gstep .num { display: inline-flex; align-items: center; justify-content: center;
    width: 30px; height: 30px; border-radius: 50%; background: var(--green-soft);
    color: var(--green); font-size: 14px; font-weight: 800; margin-bottom: 10px; }
  .gstep p { font-size: 17px; margin: 0; max-width: 520px; }
  .gstep .phone { max-width: 260px; justify-self: center; }
  .shot { position: relative; }
  .shot img { display: block; width: 100%; border-radius: 28px; }
  .tap { position: absolute; border: 3px solid var(--tap); pointer-events: none; }
  .tap.ring { border-radius: 50%; box-shadow: 0 0 0 6px var(--tap-soft); }
  .tap.zone { border-radius: 14px; background: var(--tap-soft); }
  .pager { display: flex; justify-content: space-between; gap: 14px; flex-wrap: wrap;
    margin: 36px 0 0; padding-top: 22px; border-top: 1px solid var(--line); }
  .pager a { text-decoration: none; font-weight: 700; font-size: 15px; max-width: 48%; }
  .pager .lbl { display: block; font-size: 12px; font-weight: 800; letter-spacing: .1em;
    text-transform: uppercase; color: var(--ink-2); }
  .pager .next { margin-left: auto; text-align: right; }
  @media (max-width: 640px) {
    .gstep { grid-template-columns: 1fr; gap: 16px; }
    .gstep .phone { max-width: 240px; }
    .pager a { max-width: 100%; }
  }
</style>'''


def head(title, description, path, image):
    url = f"{SITE}/{path}"
    t, d = e(title), e(description)
    up = "../" if path.startswith("guides/") else ""
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t}</title>
<meta name="description" content="{d}">
<link rel="icon" href="{up}img/app-icon.png">
<link rel="stylesheet" href="{up}style.css">
<link rel="canonical" href="{url}">
{STYLE}
<meta property="og:type" content="article">
<meta property="og:site_name" content="Camipack">
<meta property="og:locale" content="en_GB">
<meta property="og:url" content="{url}">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:image" content="{SITE}/{image}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{t}">
<meta name="twitter:description" content="{d}">
<meta name="twitter:image" content="{SITE}/{image}">
</head>
<body>
<div class="wrap">
'''


def end(up):
    return f"\n{footer(up)}\n</div>\n</body>\n</html>\n"


def shot_for(guide, n, meta_step, placeholders):
    """(src relative to guides/, alt-ready flag) or None. A real capture wins
    over a placeholder, so a capture run needs no edit here to take effect."""
    captured = OUT / "img" / f"{guide['slug']}-{n}.jpg"
    if captured.exists():
        return f"img/{captured.name}"
    if meta_step.get("placeholder"):
        placeholders.append(f"{guide['slug']} step {n}")
        return f"../img/{meta_step['placeholder']}"
    return None


def paragraphs(text):
    return "\n".join(f"  <p class=\"lede\">{e(p)}</p>" for p in text.split("\n\n"))


def guide_page(guide, meta, prev, nxt, version, updated, placeholders):
    steps = guide["steps"]
    title = meta.get("title", guide["title"])
    minutes = meta.get("minutes", 1)
    n_steps = f"{len(steps)} step{'s' if len(steps) != 1 else ''}"
    out = [head(f"{title} — Camipack guide", guide["body"].split("\n\n")[0],
                f"guides/{guide['slug']}.html", "img/shot-trip.png"), header("../", ""), ""]
    out.append(f'  <p class="eyebrow">Guide · {n_steps} · {minutes} min</p>')
    out.append(f"  <h1>{e(title)}</h1>")
    out.append(f'  <div class="chips"><span class="chip">Camipack {e(version)}</span>'
               f'<span class="chip">iPhone</span><span class="chip">Updated {e(updated)}</span></div>')
    out.append(paragraphs(guide["body"]))
    # The deep link only means something on an iPhone with the app; anywhere
    # else the same spot offers the App Store. Decided in the browser, because
    # the page is static.
    if guide.get("showMe"):
        out.append(f'''  <p class="badges">
    <a class="open-app" id="open-app" href="{e(guide['showMe'])}" hidden>Open in Camipack ›</a>
    <a class="store-badge" id="get-app" href="{STORE}">Download on the App Store</a>
  </p>
  <script>
    if (/iPhone/.test(navigator.userAgent)) {{
      document.getElementById('open-app').hidden = false;
      document.getElementById('get-app').hidden = true;
    }}
  </script>''')
    else:
        out.append(f'  <p class="badges"><a class="store-badge" href="{STORE}">Download on the App Store</a></p>')

    out.append('  <ol class="gsteps">')
    for i, step in enumerate(steps, 1):
        ms = meta.get("steps", {}).get(str(i), {})
        src = shot_for(guide, i, ms, placeholders)
        text = e(step["text"])
        if src is None:
            out.append(f'    <li class="gstep noshot"><div><span class="num">{i}</span><p>{text}</p></div></li>')
            continue
        tap = ms.get("tap")
        overlay = ""
        if tap:
            overlay = (f'<span class="tap {e(tap.get("shape", "ring"))}" aria-hidden="true" '
                       f'style="left:{tap["x"]}%;top:{tap["y"]}%;width:{tap["w"]}%;height:{tap["h"]}%"></span>')
        ph = ' data-placeholder="true"' if src.startswith("../img/") else ""
        out.append(f'''    <li class="gstep"><div><span class="num">{i}</span><p>{text}</p></div>
      <div class="phone"><div class="shot"{ph}><img src="{src}" alt="Step {i}: {e(guide['title'])}" loading="lazy">{overlay}</div></div></li>''')
    out.append("  </ol>")

    out.append('  <nav class="pager" aria-label="More guides">')
    if prev:
        out.append(f'    <a class="prev" href="{prev[0]}.html"><span class="lbl">‹ Previous</span>{e(prev[1])}</a>')
    out.append('    <a href="index.html"><span class="lbl">All guides</span>Guides</a>' if not nxt else "")
    if nxt:
        out.append(f'    <a class="next" href="{nxt[0]}.html"><span class="lbl">Next ›</span>{e(nxt[1])}</a>')
    out.append("  </nav>")
    return "\n".join(x for x in out if x != "") + end("../")


def index_page(guides, metas):
    out = [head("Guides — Camipack", "Step-by-step guides for Camipack, with a screenshot for every tap: "
                "planning a trip, flights, routes, sharing, packing, budget, offline maps and more.",
                "guides/index.html", "img/shot-trip.png"), header("../", "guides/index.html"), ""]
    out.append('  <p class="eyebrow">Guides</p>')
    out.append("  <h1>How to do things in Camipack</h1>")
    out.append('  <p class="lede">The same steps as Help inside the app, with a picture of every screen and '
               'the spot to tap marked in orange.</p>')
    out.append('''  <label class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input type="search" id="q" placeholder="Search guides — “offline”, “share”, “packing”…" aria-label="Search guides" autocomplete="off"></label>''')

    def search_text(g, m):
        words = " ".join([m.get("title", ""), m.get("card", ""), g["title"], g["body"]]
                         + [s["text"] for s in g["steps"]])
        return e(words.lower())

    def meta_line(g, m):
        n = len(g["steps"])
        return f"{n} step{'s' if n != 1 else ''} · {m.get('minutes', 1)} min"

    featured = [g for g in guides if metas[g["slug"]].get("featured")]
    rest = [g for g in guides if not metas[g["slug"]].get("featured")]
    for g in featured:
        m = metas[g["slug"]]
        out.append(f'''  <a class="card guide-card featured" href="{g['slug']}.html" data-q="{search_text(g, m)}">
    <div class="icon" aria-hidden="true">{m.get('icon', '')}</div>
    <div><h3>{e(m.get('card', g['title']))}</h3><p>{e(m.get('blurb', ''))} · {meta_line(g, m)}</p></div>
  </a>''')
    out.append('  <div class="grid" id="guides">')
    for g in rest:
        m = metas[g["slug"]]
        out.append(f'''    <a class="card guide-card" href="{g['slug']}.html" data-q="{search_text(g, m)}">
      <div class="icon" aria-hidden="true">{m.get('icon', '')}</div>
      <h3>{e(m.get('card', g['title']))}</h3>
      <p class="meta">{meta_line(g, m)}</p>
    </a>''')
    out.append("  </div>")
    out.append('  <p class="empty" id="none" hidden>No guide matches that. Try fewer words, or '
               '<a href="../support.html">ask on the Support page</a>.</p>')
    # Every word must match somewhere in the guide, like the app's Help search.
    out.append('''  <script>
    (function () {
      var q = document.getElementById('q'), none = document.getElementById('none');
      var cards = document.querySelectorAll('.guide-card');
      q.addEventListener('input', function () {
        var words = q.value.toLowerCase().split(/\\s+/).filter(Boolean), shown = 0;
        for (var i = 0; i < cards.length; i++) {
          var text = cards[i].getAttribute('data-q');
          var hit = words.every(function (w) { return text.indexOf(w) !== -1; });
          cards[i].hidden = !hit;
          if (hit) { shown++; }
        }
        none.hidden = shown > 0;
      });
    })();
  </script>''')
    return "\n".join(out) + end("../")


def update_sitemap(slugs):
    path = DOCS / "sitemap.xml"
    xml = path.read_text()
    xml = re.sub(r"  <url>\n    <loc>https://camipack\.com/guides/[^<]+</loc>\n  </url>\n", "", xml)
    entries = "".join(f"  <url>\n    <loc>{SITE}/guides/{p}</loc>\n  </url>\n"
                      for p in ["index.html"] + [f"{s}.html" for s in slugs])
    path.write_text(xml.replace("</urlset>", entries + "</urlset>"))


def add_nav_item():
    """Puts Guides after How it works in every English page's header — or
    first, on how-it-works.html itself, which leaves itself out. Idempotent.
    The translated folders wait for translated guides."""
    item = '<a href="guides/index.html">Guides</a>'
    for page in sorted(DOCS.glob("*.html")):
        text = page.read_text()
        if item in text or '<div class="menu-panel">' not in text:
            continue
        hiw = '<div class="menu-panel"><a href="how-it-works.html">How it works</a>'
        if hiw in text:
            text = text.replace(hiw, hiw + item, 1)
        else:
            text = text.replace('<div class="menu-panel">', '<div class="menu-panel">' + item, 1)
        page.write_text(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--updated", default=datetime.date.today().strftime("%-d %b %Y"))
    args = ap.parse_args()

    data = json.loads((ROOT / "tools" / "guides.json").read_text())
    metas = json.loads((ROOT / "tools" / "guides-meta.json").read_text())["guides"]
    guides = data["guides"]
    missing = [g["slug"] for g in guides if g["slug"] not in metas]
    if missing:
        sys.exit(f"guides-meta.json has no entry for: {', '.join(missing)}")
    # The featured guide leads, everywhere: index, and the prev/next chain.
    guides.sort(key=lambda g: not metas[g["slug"]].get("featured"))
    version = ".".join(data["appVersion"].split(".")[:2])

    OUT.mkdir(exist_ok=True)
    placeholders = []
    order = [(g["slug"], metas[g["slug"]].get("title", g["title"])) for g in guides]
    for i, g in enumerate(guides):
        prev = order[i - 1] if i > 0 else None
        nxt = order[i + 1] if i + 1 < len(order) else None
        (OUT / f"{g['slug']}.html").write_text(
            guide_page(g, metas[g["slug"]], prev, nxt, version, args.updated, placeholders))
    (OUT / "index.html").write_text(index_page(guides, metas))
    update_sitemap([g["slug"] for g in guides])
    add_nav_item()

    print(f"wrote {len(guides)} guides + index to {OUT.relative_to(ROOT)}")
    if placeholders:
        print(f"{len(placeholders)} steps still show a placeholder screenshot:")
        for p in placeholders:
            print(f"  {p}")


if __name__ == "__main__":
    main()
