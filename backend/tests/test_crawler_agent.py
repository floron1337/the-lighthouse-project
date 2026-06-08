from __future__ import annotations

from datetime import datetime, timezone

import pytest

import app.agents.crawler_agent as crawler_agent
from app.agents.crawler_agent import NewsCrawlerAgent, _rank_articles
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


def _article(
    title: str,
    body: str,
    source_id: str,
    source_name: str,
    url: str,
    country: str = "GB",
) -> Article:
    return Article(
        title=title,
        full_text=body,
        url=url,
        source_id=source_id,
        source_name=source_name,
        country=country,
        published_at=datetime.now(timezone.utc),
        language="en",
    )


@pytest.mark.asyncio
async def test_romanian_query_searches_romanian_results_and_keeps_real_articles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str | None]] = []

    async def fake_expand(query: str, llm_service: MockLLMService) -> list[str]:
        return [query]

    async def fake_newsapi(
        query: str,
        language: str | None = "en",
        **_: object,
    ) -> list[Article]:
        calls.append(("newsapi", language))
        return []

    async def fake_gnews(query: str, language: str = "en", **_: object) -> list[Article]:
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

    async def fake_newsapi(
        query: str,
        language: str | None = "en",
        **_: object,
    ) -> list[Article]:
        return []

    async def fake_gnews(query: str, language: str = "en", **_: object) -> list[Article]:
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

    async def fake_newsapi(
        query: str,
        language: str | None = "en",
        **_: object,
    ) -> list[Article]:
        return []

    async def fake_gnews(query: str, language: str = "en", **_: object) -> list[Article]:
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


def test_rank_articles_prioritises_topic_relevance_and_limits_repeat_sources() -> None:
    relevant_primary = _article(
        "Zelenskiy invites Putin to Ukraine ceasefire talks",
        "Ukraine's president proposed direct ceasefire talks with Russia after renewed diplomatic pressure.",
        "irish_times",
        "The Irish Times",
        "https://example.com/ukraine-ceasefire-talks",
    )
    relevant_secondary = _article(
        "Russian drone strikes kill two in Ukraine",
        "World leaders discussed pressure on Moscow as Ukraine called for ceasefire negotiations.",
        "the_punch",
        "The Punch",
        "https://example.com/russian-drone-ukraine",
        country="NG",
    )
    same_source_extra = _article(
        "NATO considers aid package for Ukraine before summit",
        "The package is linked to ceasefire talks and Ukraine's negotiating position.",
        "crypto_briefing",
        "Crypto Briefing",
        "https://example.com/ukraine-aid-1",
        country="XX",
    )
    same_source_third = _article(
        "Zelenskiy letter seeks Ukraine peace talks",
        "The Ukraine proposal asks Russia to enter ceasefire talks.",
        "crypto_briefing",
        "Crypto Briefing",
        "https://example.com/ukraine-aid-2",
        country="XX",
    )
    same_source_over_limit = _article(
        "Ukraine ceasefire diplomacy continues",
        "Ukraine ceasefire talks continue while negotiators discuss Russia's position.",
        "crypto_briefing",
        "Crypto Briefing",
        "https://example.com/ukraine-aid-3",
        country="XX",
    )
    syndicated_duplicate = _article(
        "Zelenskiy invites Putin to Ukraine ceasefire talks",
        "A syndicated copy says Ukraine proposed direct ceasefire talks with Russia.",
        "wire_copy",
        "Wire Copy",
        "https://example.com/wire-copy",
        country="FR",
    )
    off_topic = _article(
        "Trump calls Iran war a military exercise as Hormuz fighting heats up",
        "The US and Iran remained locked in conflict over the Strait of Hormuz.",
        "fortune",
        "Fortune",
        "https://example.com/iran-hormuz",
        country="US",
    )
    generic_links = _article(
        "Links 6/7/2026",
        "A collection of science, markets, and technology links from around the web.",
        "nakedcapitalism",
        "Naked Capitalism",
        "https://example.com/links",
        country="US",
    )

    ranked = _rank_articles(
        [
            off_topic,
            generic_links,
            same_source_extra,
            relevant_secondary,
            same_source_third,
            syndicated_duplicate,
            relevant_primary,
            same_source_over_limit,
        ],
        "Ukraine ceasefire talks",
        ["Ukraine ceasefire talks", "Russia Ukraine peace negotiations 2026"],
    )

    assert ranked[0] == relevant_primary
    assert off_topic not in ranked
    assert generic_links not in ranked
    assert syndicated_duplicate not in ranked
    assert sum(article.source_id == "crypto_briefing" for article in ranked) == 2
