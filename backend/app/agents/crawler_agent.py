from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app.agents.extractor import extract_and_dedupe
from app.agents.query_expander import expand
from app.agents.searchers.gnews import search_gnews
from app.agents.searchers.newsapi import search_newsapi
from app.models.article import Article, ArticleBundle
from app.services.llm_service import LLMService

# Five diverse mock articles injected when real searchers don't return enough
# distinct sources (< 3 unique source_ids) — removed once THE-8 is implemented.
_MOCK_TEMPLATE: list[tuple[str, str, str, str]] = [
    ("{q} — Analysis", "bbc_news", "BBC News", "GB"),
    ("{q} — Perspective", "aljazeera", "Al Jazeera", "QA"),
    ("{q} — State Media Report", "xinhua", "Xinhua", "CN"),
    ("{q} — Wire Report", "reuters", "Reuters", "GB"),
    ("{q} — Commentary", "rt", "RT", "RU"),
]


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
        sub_queries = await expand(query, self.llm_service)

        tasks = [search_newsapi(q) for q in sub_queries] + [
            search_gnews(q) for q in sub_queries
        ]
        results = await asyncio.gather(*tasks)
        raw_articles: list[Article] = [a for batch in results for a in batch]

        # Inject mock diversity until THE-8 makes searchers return varied sources
        if len({a.source_id for a in raw_articles}) < 3:
            raw_articles = self._mock_articles(query)

        articles = await extract_and_dedupe(raw_articles)

        return ArticleBundle(
            query=query,
            articles=articles,
            sources_covered=list({a.source_id for a in articles}),
            countries_covered=list({a.country for a in articles}),
            crawl_timestamp=datetime.now(timezone.utc),
        )

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
