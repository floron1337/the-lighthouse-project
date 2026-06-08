from __future__ import annotations

import pytest

from app.agents.orchestrator import process_query


@pytest.fixture(autouse=True)
def force_mock_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep orchestrator tests offline even when Ollama is not running."""
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.mark.asyncio
async def test_process_query_yields_articles_then_report() -> None:
    """process_query must yield ≥1 article events then exactly one bias_report."""
    events: list[dict] = []
    async for event in process_query("EU AI Act"):
        events.append(event)

    types = [e["type"] for e in events]
    assert "article" in types, "Expected at least one article event"
    assert types.count("bias_report") == 1, "Expected exactly one bias_report event"
    assert types[-1] == "bias_report", "bias_report must be the final event"


@pytest.mark.asyncio
async def test_article_event_has_required_fields() -> None:
    """Each article event must carry the fields the frontend expects."""
    required = {"title", "url", "source_id", "source_name", "country", "published_at"}
    async for event in process_query("South China Sea"):
        if event["type"] == "article":
            missing = required - set(event["data"].keys())
            assert not missing, f"Article event missing fields: {missing}"
            return
    pytest.fail("No article event was yielded")


@pytest.mark.asyncio
async def test_bias_report_has_required_fields() -> None:
    """The bias_report event must contain all top-level BiasReport fields."""
    required = {
        "topic",
        "consensus_facts",
        "disputed_framings",
        "per_article",
        "geopolitical_patterns",
        "balanced_summary",
        "methodology_note",
    }
    async for event in process_query("climate summit"):
        if event["type"] == "bias_report":
            missing = required - set(event["data"].keys())
            assert not missing, f"BiasReport missing fields: {missing}"
            assert isinstance(event["data"]["consensus_facts"], list)
            assert isinstance(event["data"]["per_article"], list)
            return
    pytest.fail("No bias_report event was yielded")


@pytest.mark.asyncio
async def test_per_article_analyses_match_articles() -> None:
    """The number of per_article analyses must equal the number of article events."""
    article_events: list[dict] = []
    report_event: dict | None = None

    async for event in process_query("Ukraine ceasefire"):
        if event["type"] == "article":
            article_events.append(event)
        elif event["type"] == "bias_report":
            report_event = event

    assert report_event is not None
    assert len(report_event["data"]["per_article"]) == len(article_events)
