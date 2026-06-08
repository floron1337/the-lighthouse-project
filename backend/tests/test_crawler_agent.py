from __future__ import annotations

from datetime import datetime, timezone

import pytest

import app.agents.crawler_agent as crawler_agent
from app.agents.crawler_agent import NewsCrawlerAgent
from app.models.article import Article


class MockLLMService:
    use_mock = True


class RealLLMService:
    use_mock = False


def _real_article() -> Article:
    return Article(
        title="Explozie cu drona in portul Galati",
        full_text="Autoritatile romane au confirmat o explozie in zona portului Galati.",
        url="https://example.ro/galati-drone",
        source_id="example_ro",
        source_name="Example Romania",
        country="RO",
        published_at=datetime.now(timezone.utc),
        language="ro",
    )


@pytest.mark.asyncio
async def test_romanian_query_searches_romanian_results_and_keeps_real_articles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str | None]] = []

    async def fake_expand(query: str, llm_service: MockLLMService) -> list[str]:
        return [query]

    async def fake_newsapi(query: str, language: str | None = "en") -> list[Article]:
        calls.append(("newsapi", language))
        return []

    async def fake_gnews(query: str, language: str = "en") -> list[Article]:
        calls.append(("gnews", language))
        return [_real_article()] if language == "ro" else []

    async def fake_extract_and_dedupe(articles: list[Article]) -> list[Article]:
        return articles

    monkeypatch.setattr(crawler_agent, "expand", fake_expand)
    monkeypatch.setattr(crawler_agent, "search_newsapi", fake_newsapi)
    monkeypatch.setattr(crawler_agent, "search_gnews", fake_gnews)
    monkeypatch.setattr(crawler_agent, "extract_and_dedupe", fake_extract_and_dedupe)

    agent = NewsCrawlerAgent(source_registry=[], llm_service=MockLLMService())
    bundle = await agent.search("explozie drona Galati")

    assert ("newsapi", None) in calls
    assert ("gnews", "ro") in calls
    assert ("gnews", "en") in calls
    assert len(bundle.articles) == 1
    assert bundle.articles[0].source_name == "Example Romania"
    assert not bundle.articles[0].full_text.startswith("Mock full-text coverage")


@pytest.mark.asyncio
async def test_crawler_uses_mock_articles_only_when_no_real_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_expand(query: str, llm_service: MockLLMService) -> list[str]:
        return [query]

    async def fake_newsapi(query: str, language: str | None = "en") -> list[Article]:
        return []

    async def fake_gnews(query: str, language: str = "en") -> list[Article]:
        return []

    async def fake_extract_and_dedupe(articles: list[Article]) -> list[Article]:
        return articles

    monkeypatch.setattr(crawler_agent, "expand", fake_expand)
    monkeypatch.setattr(crawler_agent, "search_newsapi", fake_newsapi)
    monkeypatch.setattr(crawler_agent, "search_gnews", fake_gnews)
    monkeypatch.setattr(crawler_agent, "extract_and_dedupe", fake_extract_and_dedupe)

    agent = NewsCrawlerAgent(source_registry=[], llm_service=MockLLMService())
    bundle = await agent.search("no matching articles")

    assert len(bundle.articles) == 5
    assert all(article.full_text.startswith("Mock full-text coverage") for article in bundle.articles)


@pytest.mark.asyncio
async def test_crawler_does_not_fabricate_articles_in_real_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_expand(query: str, llm_service: RealLLMService) -> list[str]:
        return [query]

    async def fake_newsapi(query: str, language: str | None = "en") -> list[Article]:
        return []

    async def fake_gnews(query: str, language: str = "en") -> list[Article]:
        return []

    async def fake_extract_and_dedupe(articles: list[Article]) -> list[Article]:
        return articles

    monkeypatch.setattr(crawler_agent, "expand", fake_expand)
    monkeypatch.setattr(crawler_agent, "search_newsapi", fake_newsapi)
    monkeypatch.setattr(crawler_agent, "search_gnews", fake_gnews)
    monkeypatch.setattr(crawler_agent, "extract_and_dedupe", fake_extract_and_dedupe)

    agent = NewsCrawlerAgent(source_registry=[], llm_service=RealLLMService())
    bundle = await agent.search("no matching articles")

    assert bundle.articles == []
