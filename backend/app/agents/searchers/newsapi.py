from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.agents.source_registry import resolve_source_name
from app.models.article import Article

logger = logging.getLogger(__name__)

_NEWSAPI_BASE = "https://newsapi.org/v2/everything"


async def search_newsapi(
    query: str,
    api_key: str = "",
    language: str | None = "en",
) -> list[Article]:
    """Search NewsAPI.org /v2/everything for articles matching query.

    Hits the endpoint with the given query string, filters to the past 7 days,
    applies a language filter when provided, and maps each result to an Article.
    Source ids are resolved against the source registry where possible.
    Requires NEWSAPI_KEY environment variable to be set.

    Args:
        query: Search string (one of the sub-queries from query_expander).
        api_key: NewsAPI key; reads from NEWSAPI_KEY env var if empty.
        language: ISO language code, or None to search without a language filter.

    Returns:
        List of Article objects. Returns an empty list on quota exhaustion or
        if no API key is configured.
    """
    key = api_key or os.getenv("NEWSAPI_KEY", "")
    if not key:
        return []

    safe_query = re.sub(r"[\"'`]", "", query).strip()
    from_date = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    params = {
        "q": safe_query,
        "from": from_date,
        "sortBy": "publishedAt",
        "pageSize": 20,
        "apiKey": key,
    }
    if language:
        params["language"] = language

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
        source_id, country = resolve_source_name(source_name)

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
                language=language or "und",
            )
        )

    return articles
