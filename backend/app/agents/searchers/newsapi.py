from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.agents.source_registry import load_registry
from app.models.article import Article

logger = logging.getLogger(__name__)

_NEWSAPI_BASE = "https://newsapi.org/v2/everything"


def _resolve_source(name: str, country: str, registry: list[dict]) -> tuple[str, str]:
    """Map a source name/country pair to (source_id, country) from the registry.

    Falls back to a slugified name and the provided country code when no match
    is found.
    """
    name_lower = name.lower()
    for entry in registry:
        if entry["name"].lower() == name_lower:
            return entry["id"], entry["country"]
        # partial match: registry name contained in API name or vice versa
        if entry["name"].lower() in name_lower or name_lower in entry["name"].lower():
            return entry["id"], entry["country"]
    slug = name_lower.replace(" ", "_").replace(".", "")
    return slug, country or "XX"


async def search_newsapi(query: str, api_key: str = "") -> list[Article]:
    """Search NewsAPI.org /v2/everything for articles matching query.

    Hits the endpoint with the given query string, filters to the past 7 days,
    requests English-language results, and maps each result to an Article.
    Source ids are resolved against the source registry where possible.
    Requires NEWSAPI_KEY environment variable to be set.

    Args:
        query: Search string (one of the sub-queries from query_expander).
        api_key: NewsAPI key; reads from NEWSAPI_KEY env var if empty.

    Returns:
        List of Article objects. Returns an empty list on quota exhaustion or
        if no API key is configured.
    """
    key = api_key or os.getenv("NEWSAPI_KEY", "")
    if not key:
        return []

    registry = load_registry()
    safe_query = re.sub(r"[\"'`]", "", query).strip()
    from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    params = {
        "q": safe_query,
        "from": from_date,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 20,
        "apiKey": key,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_NEWSAPI_BASE, params=params)
            if resp.status_code == 429:
                logger.warning("NewsAPI rate limit hit for query: %s", query)
                return []
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("NewsAPI request failed: %s", exc)
        return []

    articles: list[Article] = []
    for item in data.get("articles", []):
        source_name = (item.get("source") or {}).get("name", "Unknown")
        source_id, country = _resolve_source(source_name, "", registry)

        try:
            published_at = datetime.fromisoformat(
                item["publishedAt"].replace("Z", "+00:00")
            )
        except (KeyError, ValueError):
            published_at = datetime.now(timezone.utc)

        articles.append(
            Article(
                title=item.get("title") or "",
                full_text=item.get("content") or item.get("description") or "",
                url=item.get("url") or "",
                source_id=source_id,
                source_name=source_name,
                country=country,
                published_at=published_at,
                language="en",
            )
        )

    return articles
