from __future__ import annotations

from datetime import datetime, timezone

from app.models.article import Article


async def search_gnews(query: str, api_key: str = "") -> list[Article]:
    """Search the GNews API /v4/search for articles matching query.

    Queries for English-language results, maps results to Article, and
    falls back gracefully if the API key is missing or quota is exhausted.
    Requires GNEWS_KEY environment variable to be set.

    Args:
        query: Search string (one of the sub-queries from query_expander).
        api_key: GNews key; reads from GNEWS_KEY env var if empty.

    Returns:
        List of Article objects. Returns an empty list on quota exhaustion.
    """
    # TODO(THE-8): implement real GNews call with httpx.AsyncClient;
    #              handle rate-limiting (10 req/day on free tier); map source names to IDs
    return [
        Article(
            title=f"[GNews] Report: {query}",
            full_text=f"Mock article text about '{query}' sourced from GNews.",
            url=f"https://gnews.example.com/article?q={query.replace(' ', '+')}",
            source_id="ap_news",
            source_name="AP News",
            country="US",
            published_at=datetime.now(timezone.utc),
            language="en",
        )
    ]
