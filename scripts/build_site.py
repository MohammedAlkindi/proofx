#!/usr/bin/env python3
"""Assemble the deployable static site under src/ from site sources in the same tree.

Vercel serves the generated files at the src/ root (HTML, nav.js, assets/, etc.)
as-is with no server build step. Source inputs live in src/components/,
src/pages/, src/scripts/, and src/static/. Run this script after editing any of
those, then commit the regenerated deploy artifacts under src/.

Usage: python scripts/build_site.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from string import Template

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
STATIC = SRC / "static"

GENERATED_COMMENT = (
    "<!-- GENERATED FILE — edit src/pages/<slug>/ or src/components/, "
    "then run scripts/build.sh. Do not hand-edit this file. -->\n"
)

# Slug -> href, used to resolve nav_active / footer_active into the matching
# anchor so it can be marked aria-current="page".
NAV_HREFS = {
    "index": "/index.html",
    "collatzx": "/collatzx.html",
    "goldbachx": "/goldbachx.html",
    "riemannx": "/riemannx.html",
    "results": "/results.html",
    "research": "/research.html",
}
FOOTER_HREFS = {
    "research": "/research.html",
    "results": "/results.html",
    "roadmap": "/roadmap.html",
    "contact": "/contact.html",
    "contribute": "/contribute.html",
    "privacy": "/privacy.html",
}

PAGES = [
    "index",
    "results",
    "ledger-viewer",
    "collatzx",
    "goldbachx",
    "riemannx",
    "research",
    "roadmap",
    "contact",
    "contribute",
    "privacy",
]

OG_IMAGE_TAG = '  <meta property="og:image" content="https://www.proofx.org/assets/og.png" />'
TWITTER_IMAGE_TAG = '  <meta name="twitter:image" content="https://www.proofx.org/assets/og.png" />'


def mark_active(html: str, href: str) -> str:
    target = f'href="{href}">'
    replacement = f'href="{href}" aria-current="page">'
    if target not in html:
        raise ValueError(f"nav/footer partial has no link matching {href!r}")
    return html.replace(target, replacement, 1)


def render_head(meta: dict) -> str:
    template = Template((SRC / "components" / "_head.html").read_text(encoding="utf-8"))
    return template.substitute(
        title=meta["title"],
        description=meta["description"],
        canonical_path=meta["canonical_path"],
        og_title=meta["og_title"],
        og_description=meta["og_description"],
        og_image_tag=OG_IMAGE_TAG if meta.get("og_image", True) else "",
        twitter_card=meta.get("twitter_card", "summary_large_image"),
        twitter_image_tag=TWITTER_IMAGE_TAG if meta.get("og_image", True) else "",
    )


def render_nav(meta: dict) -> str:
    nav = (SRC / "components" / "_nav.html").read_text(encoding="utf-8")
    active = meta.get("nav_active")
    if active:
        nav = mark_active(nav, NAV_HREFS[active])
    return nav


def render_footer(meta: dict) -> str:
    footer = (SRC / "components" / "_footer.html").read_text(encoding="utf-8")
    active = meta.get("footer_active")
    if active:
        footer = mark_active(footer, FOOTER_HREFS[active])
    return footer


def render_page(slug: str) -> str:
    page_dir = SRC / "pages" / slug
    meta = json.loads((page_dir / "meta.json").read_text(encoding="utf-8"))
    content = (page_dir / "content.html").read_text(encoding="utf-8")

    script_path = page_dir / "script.js"
    script_tag = ""
    if script_path.exists():
        script_tag = f"  <script>\n{script_path.read_text(encoding='utf-8')}  </script>\n"

    body_class = meta.get("body_class")
    main_open = f'  <main id="main" class="{body_class}">' if body_class else '  <main id="main">'

    return (
        GENERATED_COMMENT
        + '<!doctype html>\n<html lang="en">\n<head>\n'
        + render_head(meta)
        + "\n</head>\n<body>\n"
        + render_nav(meta)
        + "\n"
        + main_open
        + "\n"
        + content
        + "  </main>\n\n"
        + render_footer(meta)
        + "\n"
        + script_tag
        + '  <script src="/nav.js"></script>\n'
        + "</body>\n</html>\n"
    )


def copy_static() -> int:
    """Copy hand-authored static files from src/static/ into the src/ deploy root."""
    count = 0
    for source in STATIC.rglob("*"):
        if source.is_dir():
            continue
        relative = source.relative_to(STATIC)
        destination = SRC / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        count += 1
    return count


def main() -> None:
    static_count = copy_static()

    for slug in PAGES:
        html = render_page(slug)
        out_path = SRC / f"{slug}.html"
        out_path.write_text(html, encoding="utf-8", newline="\n")

    nav_js = (SRC / "scripts" / "nav.js").read_text(encoding="utf-8")
    nav_js_comment = "// GENERATED FILE — edit src/scripts/nav.js, then run scripts/build.sh\n"
    (SRC / "nav.js").write_text(nav_js_comment + nav_js, encoding="utf-8", newline="\n")

    print(
        f"{len(PAGES)} pages generated into src/, "
        f"plus src/nav.js and {static_count} static files"
    )


if __name__ == "__main__":
    main()
