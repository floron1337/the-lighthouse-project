from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
import logging
import math
import re
from urllib.parse import urlparse

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
_MIN_RELEVANCE_SCORE = 2.2
_MAX_ARTICLES_PER_SOURCE = 2

_QUERY_STOPWORDS = {
    "about",
    "after",
    "against",
    "amid",
    "and",
    "are",
    "between",
    "for",
    "from",
    "how",
    "international",
    "latest",
    "news",
    "over",
    "reactions",
    "response",
    "talks",
    "the",
    "this",
    "update",
    "updates",
    "what",
    "with",
    "world",
    "year",
}
_GENERIC_TITLE_PATTERNS = (
    re.compile(r"^links\s+\d", re.IGNORECASE),
    re.compile(r"^live updates?\b", re.IGNORECASE),
    re.compile(r"^morning briefing\b", re.IGNORECASE),
    re.compile(r"^world brief\b", re.IGNORECASE),
)
_LOW_SIGNAL_TITLE_TERMS = {
    "book review",
    "market size",
    "currency defense",
    "stock market",
    "crypto market",
    "press release",
}


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


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'-]{2,}", text.casefold())
        if token not in _QUERY_STOPWORDS and not token.isdigit()
    }


def _topic_tokens(query: str, sub_queries: list[str]) -> set[str]:
    tokens = _tokens(query)
    for sub_query in sub_queries:
        tokens.update(_tokens(sub_query))
    return tokens


def _original_query_tokens(query: str) -> set[str]:
    return _tokens(query)


def _article_relevance(article: Article, query: str, sub_queries: list[str]) -> float:
    title = article.title or ""
    body = article.full_text or ""
    url_path = urlparse(article.url).path.replace("-", " ").replace("_", " ")

    title_tokens = _tokens(title)
    body_tokens = _tokens(body[:1600])
    url_tokens = _tokens(url_path)
    all_tokens = title_tokens | body_tokens | url_tokens
    topic_tokens = _topic_tokens(query, sub_queries)
    original_tokens = _original_query_tokens(query)

    if not topic_tokens or not all_tokens:
        return 0.0

    original_overlap = original_tokens & all_tokens
    topic_overlap = topic_tokens & all_tokens
    title_overlap = topic_tokens & title_tokens

    score = 0.0
    score += 2.6 * len(original_overlap)
    score += 1.25 * len(title_overlap)
    score += 0.65 * len(topic_overlap)
    score += 0.35 * len(topic_tokens & url_tokens)

    lowered_title = title.casefold()
    lowered_text = f"{title} {body[:800]}".casefold()
    if query.casefold() in lowered_text:
        score += 4.0
    for sub_query in sub_queries:
        if sub_query.casefold() in lowered_text:
            score += 1.5

    if article.source_id == "unknown_source" or article.country == "XX":
        score -= 0.35
    if len(body.strip()) < 120:
        score -= 0.5
    if any(pattern.search(title) for pattern in _GENERIC_TITLE_PATTERNS):
        score -= 4.0
    if any(term in lowered_title for term in _LOW_SIGNAL_TITLE_TERMS):
        score -= 2.0

    # Require at least one original topic term unless the exact query/sub-query
    # appears; this blocks broad geopolitical false positives.
    has_phrase_match = query.casefold() in lowered_text or any(
        sub_query.casefold() in lowered_text for sub_query in sub_queries
    )
    if original_tokens and not original_overlap and not has_phrase_match:
        score -= 3.5

    coverage = len(topic_overlap) / max(len(topic_tokens), 1)
    score += math.log1p(max(len(body), len(title))) * 0.15
    score += coverage * 2.0
    return round(score, 3)


def _rank_articles(
    articles: list[Article],
    query: str,
    sub_queries: list[str],
    *,
    min_score: float = _MIN_RELEVANCE_SCORE,
) -> list[Article]:
    scored = [
        (_article_relevance(article, query, sub_queries), article)
        for article in articles
        if article.url and article.title
    ]
    if not scored:
        return []

    scored.sort(
        key=lambda item: (
            item[0],
            item[1].country != "XX",
            item[1].published_at,
        ),
        reverse=True,
    )

    selected: list[Article] = []
    per_source: dict[str, int] = {}
    selected_story_tokens: list[set[str]] = []

    def story_tokens(article: Article) -> set[str]:
        return _tokens(f"{article.title} {article.full_text[:360]}")

    def is_story_duplicate(article: Article) -> bool:
        article_tokens = story_tokens(article)
        if len(article_tokens) < 5:
            return False
        for existing_tokens in selected_story_tokens:
            overlap = article_tokens & existing_tokens
            similarity = len(overlap) / max(len(article_tokens | existing_tokens), 1)
            if len(overlap) >= 7 and similarity >= 0.48:
                return True
        return False

    for score, article in scored:
        if score < min_score:
            continue
        if per_source.get(article.source_id, 0) >= _MAX_ARTICLES_PER_SOURCE:
            continue
        if is_story_duplicate(article):
            continue
        selected.append(article)
        selected_story_tokens.append(story_tokens(article))
        per_source[article.source_id] = per_source.get(article.source_id, 0) + 1
        if len(selected) >= _MAX_ARTICLES:
            return selected

    # If the APIs return sparse results, fill the tail with the best remaining
    # candidates rather than failing the search outright.
    if len(selected) < 4:
        selected_urls = {article.url for article in selected}
        for _, article in scored:
            if article.url in selected_urls:
                continue
            if per_source.get(article.source_id, 0) >= _MAX_ARTICLES_PER_SOURCE:
                continue
            if is_story_duplicate(article):
                continue
            selected.append(article)
            selected_story_tokens.append(story_tokens(article))
            selected_urls.add(article.url)
            per_source[article.source_id] = per_source.get(article.source_id, 0) + 1
            if len(selected) >= min(_MAX_ARTICLES, 6):
                break

    return selected


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

        raw_articles: list[Article] = []

        for q in sub_queries:
            newsapi_language = None if "ro" in languages else "en"
            raw_articles.extend(
                await search_newsapi(
                    q,
                    language=newsapi_language,
                    llm_service=self.llm_service,
                )
            )

            gnews_results = await asyncio.gather(
                *(
                    search_gnews(
                        q,
                        language=language,
                        llm_service=self.llm_service,
                    )
                    for language in languages
                ),
                return_exceptions=True,
            )
            for result in gnews_results:
                if isinstance(result, Exception):
                    logger.warning("GNews search task failed for query %r: %s: %r", q, type(result).__name__, result)
                    continue
                raw_articles.extend(result)

        deduped = await extract_and_dedupe(raw_articles)
        ranked = _rank_articles(deduped, query, sub_queries)
        if ranked:
            for article in ranked:
                yield article
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
