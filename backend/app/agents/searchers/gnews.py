from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.agents.source_registry import resolve_source_name
from app.models.article import Article

logger = logging.getLogger(__name__)

_GNEWS_BASE = "https://gnews.io/api/v4/search"
_RATE_LIMITED_UNTIL: datetime | None = None
_RATE_LIMIT_COOLDOWN_SECONDS = 60


def _sanitize_query(query: str) -> str:
    safe = re.sub(r"[\"'`]", "", query)
    safe = re.sub(r"\s+[-–—]+\s+", " ", safe)
    safe = re.sub(r"\s+", " ", safe).strip()
    return safe[:200]


async def search_gnews(
    query: str,
    api_key: str = "",
    language: str = "en",
) -> list[Article]:
    """Search the GNews API /v4/search for articles matching query.

    Queries for results in the requested language, maps results to Article, and
    falls back gracefully if the API key is missing or quota is exhausted.
    Requires GNEWS_KEY environment variable to be set.

    Args:
        query: Search string (one of the sub-queries from query_expander).
        api_key: GNews key; reads from GNEWS_KEY env var if empty.
        language: ISO language code supported by GNews.

    Returns:
        List of Article objects. Returns an empty list on quota exhaustion or
        if no API key is configured.
    """
    key = api_key or os.getenv("GNEWS_KEY", "")
    if not key:
        return []

    global _RATE_LIMITED_UNTIL
    now = datetime.now(timezone.utc)
    if _RATE_LIMITED_UNTIL and now < _RATE_LIMITED_UNTIL:
        logger.info("Skipping GNews query during rate-limit cooldown: %s", query)
        return []

    safe_query = _sanitize_query(query)
    if not safe_query:
        return []

    params = {
        "q": safe_query,
        "lang": language,
        "max": 10,
        "token": key,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_GNEWS_BASE, params=params)
            if resp.status_code == 429:
                _RATE_LIMITED_UNTIL = datetime.now(timezone.utc) + timedelta(
                    seconds=_RATE_LIMIT_COOLDOWN_SECONDS
                )
                logger.warning("GNews rate limit hit for query: %s", safe_query)
                return []
            if resp.status_code == 400:
                logger.warning("GNews rejected query (400): %s", safe_query)
                return []
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("GNews request failed: %s", exc)
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
                language=language,
            )
        )

    return articles
