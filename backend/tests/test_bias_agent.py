from __future__ import annotations

from datetime import datetime, timezone

import pytest

import app.agents.bias_agent as bias_agent
from app.agents.bias_agent import BiasAnalystAgent
from app.models.article import Article, ArticleBundle


class MockLLMService:
    use_mock = True


def _article(source_id: str, source_name: str, country: str) -> Article:
    return Article(
        title=f"{source_name} report",
        full_text="A short article body.",
        url=f"https://example.com/{source_id}",
        source_id=source_id,
        source_name=source_name,
        country=country,
        published_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_bias_agent_falls_back_when_one_analysis_task_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_analyze = bias_agent.analyze

    async def flaky_analyze(*, article: Article, source_profile: dict, llm_service: MockLLMService):
        if article.source_id == "bbc_news":
            raise TimeoutError("ollama timed out")
        return await original_analyze(
            article=article,
            source_profile=source_profile,
            llm_service=llm_service,
        )

    monkeypatch.setattr(bias_agent, "analyze", flaky_analyze)

    bundle = ArticleBundle(
        query="EU AI Act",
        articles=[
            _article("bbc_news", "BBC News", "GB"),
            _article("reuters", "Reuters", "GB"),
        ],
        sources_covered=["bbc_news", "reuters"],
        countries_covered=["GB"],
    )
    agent = BiasAnalystAgent(source_registry=[], llm_service=MockLLMService())

    report = await agent.analyze(bundle)

    assert len(report.per_article) == 2
    assert {analysis.article_url for analysis in report.per_article} == {
        "https://example.com/bbc_news",
        "https://example.com/reuters",
    }
