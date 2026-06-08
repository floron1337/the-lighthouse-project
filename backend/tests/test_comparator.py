from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.agents.comparator import compare
from app.models.article import Article
from app.models.bias_report import ArticleBiasAnalysis


class FailingLLMService:
    use_mock = False

    async def complete(self, prompt: str) -> str:
        raise ConnectionError("ollama unavailable")


class MockLLMService:
    use_mock = True


class FakeLLMService:
    use_mock = False

    def __init__(self, response: str) -> None:
        self.response = response

    async def complete(self, prompt: str) -> str:
        return self.response


ANALYSIS = ArticleBiasAnalysis(
    article_url="https://example.com/article",
    source_id="bbc_news",
    overall_bias_direction="pro-Western",
    confidence=0.8,
    framing_analysis="Institutional framing.",
    loaded_terms=[],
    omissions=[],
    sentiment_score=0.0,
    attribution_balance="Quotes officials.",
)


def _article(source_id: str, source_name: str) -> Article:
    return Article(
        title="Romania says a drone exploded near the Galati port without casualties",
        full_text=(
            "Romania officials said a drone exploded near the Galati port without casualties. "
            "Authorities said the incident occurred near the Ukrainian border."
        ),
        url=f"https://example.com/{source_id}",
        source_id=source_id,
        source_name=source_name,
        country="RO",
        published_at=datetime.now(timezone.utc),
    )


def _analysis(
    source_id: str,
    direction: str,
    framing: str,
    loaded_terms: list[str],
) -> ArticleBiasAnalysis:
    return ArticleBiasAnalysis(
        article_url=f"https://example.com/{source_id}",
        source_id=source_id,
        overall_bias_direction=direction,
        confidence=0.82,
        framing_analysis=framing,
        loaded_terms=loaded_terms,
        omissions=["NATO response"],
        sentiment_score=-0.1,
        attribution_balance="Quotes officials and military analysts.",
    )


ARTICLES = [
    _article("bbc_news", "BBC News"),
    _article("reuters", "Reuters"),
    _article("rt", "RT"),
]

ANALYSES = [
    _analysis("bbc_news", "pro-Western", "Frames the blast as a security spillover from Russia's war.", ["security", "spillover"]),
    _analysis("reuters", "neutral", "Frames the event as a verified border incident requiring confirmation.", ["verified", "border"]),
    _analysis("rt", "pro-BRICS", "Frames the story as Western alarmism around Russia accusations.", ["alarmism", "accusations"]),
]

SOURCE_PROFILES = [
    {"source_id": "bbc_news", "alliance_bloc": "NATO/Five Eyes", "region": "Western Europe"},
    {"source_id": "reuters", "alliance_bloc": "NATO/Five Eyes", "region": "Western Europe"},
    {"source_id": "rt", "alliance_bloc": "BRICS", "region": "Eastern Europe"},
]


@pytest.mark.asyncio
async def test_compare_falls_back_when_llm_is_unavailable() -> None:
    report = await compare([ANALYSIS], topic="EU AI Act", llm_service=FailingLLMService())

    assert report.topic == "EU AI Act"
    assert report.per_article == [ANALYSIS]
    assert report.balanced_summary


@pytest.mark.asyncio
async def test_compare_derives_consensus_framings_and_geopolitical_patterns() -> None:
    report = await compare(
        ANALYSES,
        topic="Romania Galati drone explosion",
        llm_service=MockLLMService(),
        articles=ARTICLES,
        source_profiles=SOURCE_PROFILES,
    )

    assert report.consensus_facts
    assert "Reported by 3 sources" in report.consensus_facts[0]
    assert len(report.disputed_framings) == 3
    assert any(framing["geopolitical_pattern"].startswith("NATO/Five Eyes") for framing in report.disputed_framings)
    assert any("NATO/Five Eyes sources" in pattern for pattern in report.geopolitical_patterns)
    assert "Romania Galati drone explosion" in report.balanced_summary


@pytest.mark.asyncio
async def test_compare_keeps_computed_fields_when_llm_response_is_partial() -> None:
    report = await compare(
        ANALYSES,
        topic="Romania Galati drone explosion",
        llm_service=FakeLLMService(json.dumps({"balanced_summary": "LLM-written summary."})),
        articles=ARTICLES,
        source_profiles=SOURCE_PROFILES,
    )

    assert report.balanced_summary == "LLM-written summary."
    assert report.consensus_facts
    assert report.disputed_framings
    assert report.geopolitical_patterns
