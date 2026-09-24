"""Dependency-light web search (DuckDuckGo HTML, no API key).

Vendored from advanced-memory-mcp's research_sources.py (same approach,
rewritten against this repo's conventions): plain httpx POST, regex title /
URL / snippet extraction, graceful empty-list degradation. Used by the chat
agent for questions outside the GTFS depot (news, comparisons, background).
"""

from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any
from urllib.parse import unquote

import httpx

logger = logging.getLogger(__name__)

_UA = {"User-Agent": "gtfs-mcp/0.1 (local research tool)"}
_ENDPOINT = "https://html.duckduckgo.com/html/"


def _strip_tags(s: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", s or "")).strip()


async def web_search(query: str, max_results: int = 8) -> dict[str, Any]:
    """DuckDuckGo HTML search. Always returns {"results": [...]} (empty on failure)."""
    results: list[dict[str, str]] = []
    query = (query or "").strip()
    if not query:
        return {"results": results}
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=_UA, follow_redirects=True) as client:
            resp = await client.post(_ENDPOINT, data={"q": query})
        if resp.status_code != 200:
            logger.warning("web_search: duckduckgo returned HTTP %s", resp.status_code)
            return {"results": results}
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', resp.text, re.S)
        snips = re.findall(r'class="result__snippet"[^>]*>(.*?)</(?:a|div)>', resp.text, re.S)
        for i, (url, title) in enumerate(links[: max(1, min(max_results, 10))]):
            m = re.search(r"uddg=([^&]+)", url)
            if m:
                url = unquote(m.group(1))
            snippet = snips[i] if i < len(snips) else ""
            results.append(
                {
                    "title": _strip_tags(title),
                    "snippet": _strip_tags(snippet)[:600],
                    "url": url,
                }
            )
    except Exception as exc:
        logger.warning("web_search failed: %s", exc)
    return {"results": results}
