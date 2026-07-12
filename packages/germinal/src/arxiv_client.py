"""arXiv client for fetching recent paper abstracts as generation context."""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_ARXIV_API = "https://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}

_DOMAIN_TO_CATS: dict[str, str] = {
    "number theory": "math.NT",
    "analytic number theory": "math.NT",
    "algebraic number theory": "math.NT",
    "graph theory": "math.CO",
    "combinatorics": "math.CO",
    "additive combinatorics": "math.CO",
    "ramsey theory": "math.CO",
    "algebraic topology": "math.AT",
    "knot theory": "math.GT",
    "group theory": "math.GR",
    "algebra": "math.RA",
    "elliptic curves": "math.NT",
    "probability": "math.PR",
    "analysis": "math.CA",
    "geometry": "math.DG",
    "logic": "math.LO",
}


def _cat_for(domain: str) -> str:
    return _DOMAIN_TO_CATS.get(domain.lower().strip(), "math")


def _text(el: ET.Element | None) -> str:
    return (el.text or "").strip() if el is not None else ""


async def fetch_context_papers(
    domain: str, max_results: int = 4
) -> list[dict[str, Any]]:
    """Return recent arXiv abstracts relevant to *domain*.

    Falls back gracefully to an empty list on any network or parse error so the
    caller never has to guard against this function raising.
    """
    cat = _cat_for(domain)
    query = f"cat:{cat} AND all:{domain.replace(' ', '+')}"
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            resp = await client.get(_ARXIV_API, params=params)
            resp.raise_for_status()
        root = ET.fromstring(resp.text)
        papers: list[dict[str, Any]] = []
        for entry in root.findall("atom:entry", _NS):
            title = _text(entry.find("atom:title", _NS))
            abstract = _text(entry.find("atom:summary", _NS))
            arxiv_id = _text(entry.find("atom:id", _NS)).split("/abs/")[-1]
            papers.append(
                {
                    "id": arxiv_id,
                    "title": title,
                    "abstract": abstract[:600],
                }
            )
        logger.info("Fetched %d arXiv papers for domain=%r", len(papers), domain)
        return papers
    except Exception as exc:
        logger.warning("arXiv fetch failed for domain=%r: %s", domain, exc)
        return []


def format_papers_for_prompt(papers: list[dict[str, Any]]) -> str:
    """Render paper list as a compact prompt snippet."""
    if not papers:
        return ""
    lines = [
        "Recent arXiv work in this area (for context — do NOT merely restate these):"
    ]
    for p in papers:
        lines.append(f"• [{p['id']}] {p['title']}: {p['abstract']}")
    return "\n".join(lines)
