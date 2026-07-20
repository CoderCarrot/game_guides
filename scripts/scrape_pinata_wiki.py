"""Build a static HTML mirror of pages linked from the Viva Pinata Fandom wiki's
Species and Plant index pages, ready to host on GitHub Pages.

Usage: python scripts/scrape_pinata_wiki.py
"""

import html
import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from bs4 import BeautifulSoup

API_URL = "https://vivapinata.fandom.com/api.php"
WIKI_BASE = "https://vivapinata.fandom.com/wiki/"
SOURCE_PAGES = [
    ("Species", "Species & Related Pages"),
    ("Plant", "Plants & Related Pages"),
]
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs"
PAGES_DIR = OUTPUT_DIR / "pages"
USER_AGENT = "vivapinata-wiki-mirror-script/1.0 (personal fan reference build; contact: codercarrot@gmail.com)"
REQUEST_DELAY_SECONDS = 0.4


def api_get(params):
    url = API_URL + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    time.sleep(REQUEST_DELAY_SECONDS)
    return data


def get_linked_titles(page):
    data = api_get({"action": "parse", "page": page, "format": "json", "prop": "links"})
    links = data.get("parse", {}).get("links", [])
    return sorted({l["*"] for l in links if l.get("ns") == 0 and "exists" in l})


def fetch_page(title):
    data = api_get(
        {"action": "parse", "page": title, "format": "json", "prop": "text", "redirects": 1}
    )
    parse = data.get("parse")
    if not parse:
        return None
    return parse["title"], parse["text"]["*"]


def slugify(title):
    normalized = unicodedata.normalize("NFKD", title)
    ascii_str = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^A-Za-z0-9]+", "_", ascii_str).strip("_")
    return slug or "page"


def clean_content(content, slug_by_title):
    soup = BeautifulSoup(content, "html.parser")

    for tag in soup.select(".mw-editsection"):
        tag.decompose()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/wiki/"):
            continue
        target = urllib.parse.unquote(href[len("/wiki/"):]).split("#")[0].replace("_", " ")
        slug = slug_by_title.get(target)
        if slug:
            a["href"] = f"./{slug}.html"
        else:
            a["href"] = WIKI_BASE + urllib.parse.quote(target.replace(" ", "_"))

    return str(soup)


PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} - Viva Pinata Wiki Mirror</title>
<link rel="stylesheet" href="../style.css">
</head>
<body>
<div class="page">
<nav class="breadcrumb"><a href="../index.html">Home</a></nav>
<article>
<h1>{title}</h1>
{body}
</article>
<footer class="attribution">
Content adapted from <a href="{source_url}" target="_blank" rel="noopener">the Viva Pinata Wiki on Fandom</a>,
available under <a href="https://www.fandom.com/licensing" target="_blank" rel="noopener">CC BY-SA</a>.
</footer>
</div>
</body>
</html>
"""

INDEX_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Viva Pinata Wiki Mirror</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="page">
<h1>Viva Pinata Wiki Mirror</h1>
<p class="intro">
A static mirror of pages linked from the
<a href="https://vivapinata.fandom.com/wiki/Species" target="_blank" rel="noopener">Species</a> and
<a href="https://vivapinata.fandom.com/wiki/Plant" target="_blank" rel="noopener">Plant</a>
index pages on the Viva Pinata Fandom wiki.
</p>
{sections}
<footer class="attribution">
Content adapted from <a href="https://vivapinata.fandom.com/" target="_blank" rel="noopener">the Viva Pinata Wiki on Fandom</a>,
available under <a href="https://www.fandom.com/licensing" target="_blank" rel="noopener">CC BY-SA</a>.
</footer>
</div>
</body>
</html>
"""

STYLE_CSS = """
:root {
  color-scheme: light dark;
  --bg: #fdfbf7;
  --fg: #2b2b2b;
  --accent: #b9532f;
  --card-bg: #ffffff;
  --border: #e4ddd0;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1c1a17;
    --fg: #ecebe7;
    --accent: #e79a63;
    --card-bg: #262320;
    --border: #3a352d;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", system-ui, -apple-system, Roboto, sans-serif;
  background: var(--bg);
  color: var(--fg);
}
.page { max-width: 900px; margin: 0 auto; padding: 1.5rem 1.25rem 3rem; }
h1 { color: var(--accent); }
a { color: var(--accent); }
.intro { opacity: 0.85; }
.breadcrumb { margin-bottom: 1rem; }
.breadcrumb a { text-decoration: none; font-weight: 600; }
article table { border-collapse: collapse; margin: 1rem 0; max-width: 100%; }
article table, article th, article td { border: 1px solid var(--border); padding: 0.4rem 0.6rem; }
article img { max-width: 100%; height: auto; }
article aside.portable-infobox {
  float: right;
  width: 270px;
  margin: 0 0 1rem 1.5rem;
  padding: 0.75rem;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 8px;
}
@media (max-width: 640px) {
  article aside.portable-infobox { float: none; width: auto; margin: 1rem 0; }
}
.section-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.4rem 1rem;
  list-style: none;
  padding: 0;
  margin: 0.5rem 0 2rem;
}
.section-grid li a { text-decoration: none; }
.section-grid li a:hover { text-decoration: underline; }
.attribution {
  margin-top: 3rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  font-size: 0.85rem;
  opacity: 0.75;
}
"""


def build_index(groups):
    sections = []
    for label, entries in groups:
        items = "\n".join(
            f'<li><a href="pages/{slug}.html">{html.escape(title)}</a></li>'
            for title, slug in sorted(entries)
        )
        sections.append(f"<h2>{html.escape(label)}</h2>\n<ul class=\"section-grid\">\n{items}\n</ul>")
    return INDEX_TEMPLATE.format(sections="\n".join(sections))


def main():
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    referenced_titles = {}
    for page, label in SOURCE_PAGES:
        print(f"Fetching links from '{page}'...")
        titles = get_linked_titles(page)
        print(f"  found {len(titles)} linked pages")
        for title in titles:
            referenced_titles.setdefault(title, set()).add(label)

    canonical_of = {}
    content_by_canonical = {}
    ordered_titles = sorted(referenced_titles)

    for i, title in enumerate(ordered_titles, 1):
        print(f"[{i}/{len(ordered_titles)}] fetching '{title}'")
        try:
            result = fetch_page(title)
        except urllib.error.URLError as exc:
            print(f"  skipped: {exc}")
            continue
        if result is None:
            print("  skipped: no content returned")
            continue
        canonical, body = result
        canonical_of[title] = canonical
        content_by_canonical.setdefault(canonical, body)

    slug_by_title = {}
    for title, canonical in canonical_of.items():
        slug = slugify(canonical)
        slug_by_title[title] = slug
        slug_by_title[canonical] = slug

    for canonical, body in content_by_canonical.items():
        slug = slug_by_title[canonical]
        cleaned = clean_content(body, slug_by_title)
        page_html = PAGE_TEMPLATE.format(
            title=html.escape(canonical),
            body=cleaned,
            source_url=WIKI_BASE + urllib.parse.quote(canonical.replace(" ", "_")),
        )
        (PAGES_DIR / f"{slug}.html").write_text(page_html, encoding="utf-8")

    groups = []
    for _, label in SOURCE_PAGES:
        entries = {
            (canonical_of[title], slug_by_title[title])
            for title, labels in referenced_titles.items()
            if label in labels and title in canonical_of
        }
        groups.append((label, entries))

    (OUTPUT_DIR / "index.html").write_text(build_index(groups), encoding="utf-8")
    (OUTPUT_DIR / "style.css").write_text(STYLE_CSS, encoding="utf-8")

    print(f"\nWrote {len(content_by_canonical)} pages to {PAGES_DIR}")
    print(f"Index written to {OUTPUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
