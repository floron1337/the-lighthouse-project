from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import logging

from app.agents.extractor import extract_and_dedupe
from app.agents.query_expander import expand
from app.agents.searchers.gnews import search_gnews
from app.agents.searchers.newsapi import search_newsapi
from app.models.article import Article, ArticleBundle
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

# Five diverse mock articles injected when real searchers don't return enough
# distinct sources (< 3 unique source_ids) — removed once THE-8 is implemented.
_MOCK_TEMPLATE: list[tuple[str, str, str, str]] = [
    ("{q} — Analysis", "bbc_news", "BBC News", "GB"),
    ("{q} — Perspective", "aljazeera", "Al Jazeera", "QA"),
    ("{q} — State Media Report", "xinhua", "Xinhua", "CN"),
    ("{q} — Wire Report", "reuters", "Reuters", "GB"),
    ("{q} — Commentary", "rt", "RT", "RU"),
]

_ROMANIAN_MARKERS = {
    "aeroport",
    "atac",
    "bucuresti",
    "că",
    "către",
    "cu",
    "de",
    "din",
    "drona",
    "dronă",
    "drone",
    "după",
    "explozie",
    "fost",
    "galati",
    "galați",
    "incendiu",
    "la",
    "marea",
    "neagră",
    "port",
    "romania",
    "românia",
    "rus",
    "rusia",
    "ucraina",
    "ucraina",
    "ucrainean",
    "un",
}
_MAX_SUB_QUERIES = 3
_MAX_ARTICLES = 12


def _looks_romanian(query: str) -> bool:
    lowered = query.lower()
    if any(ch in lowered for ch in "ăâîșşțţ"):
        return True
    words = {word.strip(".,:;!?()[]{}\"'") for word in lowered.split()}
    return len(words & _ROMANIAN_MARKERS) >= 2


def _search_languages(query: str) -> list[str]:
    if _looks_romanian(query):
        return ["ro", "en"]
    return ["en"]


class NewsCrawlerAgent:
    """Agent 1 — finds articles on the user's query from diverse global sources.

    Orchestrates: query expansion → parallel multi-source search →
    article extraction → deduplication → ArticleBundle output.

    The leaf functions (expand, search_*, extract_and_dedupe) are stubbed;
    this class wires them together in the real async pipeline.
    """

    def __init__(self, source_registry: list[dict], llm_service: LLMService) -> None:
        self.source_registry = source_registry
        self.llm_service = llm_service

    async def search(self, query: str) -> ArticleBundle:
        """Run the full crawl pipeline for the given query.

        Returns an ArticleBundle with deduplicated articles from multiple sources.
        """
        articles = [article async for article in self.iter_articles(query)]

        return ArticleBundle(
            query=query,
            articles=articles,
            sources_covered=list({a.source_id for a in articles}),
            countries_covered=list({a.country for a in articles}),
            crawl_timestamp=datetime.now(timezone.utc),
        )

    async def iter_articles(self, query: str) -> AsyncGenerator[Article, None]:
        """Yield deduplicated articles as each search batch becomes available."""
        sub_queries = await expand(query, self.llm_service)
        sub_queries = sub_queries[:_MAX_SUB_QUERIES]
        languages = _search_languages(query)

        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        yielded = 0

        async def emit_batch(raw_articles: list[Article]) -> AsyncGenerator[Article, None]:
            nonlocal yielded
            for article in await extract_and_dedupe(raw_articles):
                title_key = article.title.strip().casefold()
                if article.url in seen_urls or title_key in seen_titles:
                    continue
                seen_urls.add(article.url)
                seen_titles.add(title_key)
                yielded += 1
                yield article
                if yielded >= _MAX_ARTICLES:
                    return

        for q in sub_queries:
            newsapi_language = None if "ro" in languages else "en"
            async for article in emit_batch(await search_newsapi(q, language=newsapi_language)):
                yield article
            if yielded >= _MAX_ARTICLES:
                return

            gnews_results = await asyncio.gather(
                *(search_gnews(q, language=language) for language in languages),
                return_exceptions=True,
            )
            for result in gnews_results:
                if isinstance(result, Exception):
                    logger.warning("GNews search task failed for query %r: %s: %r", q, type(result).__name__, result)
                    continue
                async for article in emit_batch(result):
                    yield article
                if yielded >= _MAX_ARTICLES:
                    return

        if yielded:
            return

        if self.llm_service.use_mock:
            logger.warning("No real articles found for query %r; using mock fallback articles.", query)
            for article in self._mock_articles(query):
                yield article
        else:
            logger.warning("No real articles found for query %r.", query)

    def _mock_articles(self, query: str) -> list[Article]:
        now = datetime.now(timezone.utc)
        return [
            Article(
                title=title.format(q=query),
                full_text=f"Mock full-text coverage of '{query}' from {name}.",
                url=f"https://{sid}.example.com/{query.replace(' ', '-')}",
                source_id=sid,
                source_name=name,
                country=country,
                published_at=now,
                language="en",
            )
            for title, sid, name, country in _MOCK_TEMPLATE
        ]
