from __future__ import annotations

from datetime import datetime, timezone

from app.models.article import Article


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
        List of Article objects. Returns an empty list on quota exhaustion.
    """
    # TODO(THE-8): implement real NewsAPI call with httpx.AsyncClient;
    #              map source names to registry IDs; handle 429 rate limiting
    return [
        Article(
            title=f"[NewsAPI] Breaking: {query}",
            full_text=f"Mock article text about '{query}' sourced from NewsAPI.",
            url=f"https://newsapi.example.com/article?q={query.replace(' ', '+')}",
            source_id="reuters",
            source_name="Reuters",
            country="GB",
            published_at=datetime.now(timezone.utc),
            language="en",
        )
    ]
