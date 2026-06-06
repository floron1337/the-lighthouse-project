from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from app.agents.article_analyzer import analyze
from app.models.article import Article


class FakeLLMService:
    use_mock = False

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.calls = 0

    async def complete(self, prompt: str) -> str:
        self.calls += 1
        return self.responses.pop(0)


class FailingLLMService:
    use_mock = False

    async def complete(self, prompt: str) -> str:
        raise ConnectionError("ollama unavailable")


ARTICLE = Article(
    title="Maritime talks resume",
    full_text="Officials from several countries resumed talks after a regional dispute.",
    url="https://example.com/article",
    source_id="bbc_news",
    source_name="BBC News",
    country="GB",
    published_at=datetime.now(timezone.utc),
)

SOURCE_PROFILE = {
    "country": "GB",
    "ownership": "state_funded",
    "known_lean": "centre",
    "alliance_bloc": "NATO/Five Eyes",
    "press_freedom_category": "satisfactory",
    "regional_context": "GB is treated as part of Western Europe.",
    "compass_baseline": {
        "economic_axis": 0.0,
        "social_axis": 0.1,
        "label": "centrist / institutional",
        "confidence": 0.65,
    },
}


@pytest.mark.asyncio
async def test_analyze_parses_and_clamps_llm_response() -> None:
    llm = FakeLLMService(
        [
            json.dumps(
                {
                    "overall_bias_direction": "neutral",
                    "confidence": 1.5,
                    "framing_analysis": "Balanced institutional framing.",
                    "loaded_terms": ["dispute"],
                    "omissions": [],
                    "sentiment_score": -2,
                    "attribution_balance": "Quotes officials from both sides.",
                    "political_compass": {
                        "economic_axis": 2,
                        "social_axis": -2,
                        "regional_context": "Compared with Western European public media.",
                        "label": "centrist / institutional",
                        "confidence": 1.2,
                    },
                }
            )
        ]
    )

    analysis = await analyze(ARTICLE, SOURCE_PROFILE, llm)

    assert analysis.confidence == 1.0
    assert analysis.sentiment_score == -1.0
    assert analysis.political_compass is not None
    assert analysis.political_compass.economic_axis == 1.0
    assert analysis.political_compass.social_axis == -1.0
    assert analysis.political_compass.confidence == 1.0


@pytest.mark.asyncio
async def test_analyze_retries_malformed_json_once() -> None:
    llm = FakeLLMService(
        [
            "not json",
            json.dumps(
                {
                    "bias_direction": "pro-Western",
                    "confidence": 0.7,
                    "framing": "Frames action as lawful defense.",
                    "loaded_language": ["deterrence"],
                    "omissions": ["Regional civilian concerns"],
                    "tone": 0.2,
                    "attribution": "Quotes NATO officials.",
                }
            ),
        ]
    )

    analysis = await analyze(ARTICLE, SOURCE_PROFILE, llm)

    assert llm.calls == 2
    assert analysis.overall_bias_direction == "pro-Western"
    assert analysis.framing_analysis == "Frames action as lawful defense."
    assert analysis.loaded_terms == ["deterrence"]
    assert analysis.political_compass is not None
    assert analysis.political_compass.label == "centrist / institutional"


@pytest.mark.asyncio
async def test_mock_analysis_is_deterministic() -> None:
    class MockLLMService:
        use_mock = True

    first = await analyze(ARTICLE, SOURCE_PROFILE, MockLLMService())
    second = await analyze(ARTICLE, SOURCE_PROFILE, MockLLMService())

    assert first.confidence == second.confidence
    assert first.sentiment_score == second.sentiment_score
    assert first.political_compass == second.political_compass


@pytest.mark.asyncio
async def test_analyze_falls_back_when_llm_is_unavailable() -> None:
    analysis = await analyze(ARTICLE, SOURCE_PROFILE, FailingLLMService())

    assert analysis.article_url == ARTICLE.url
    assert analysis.source_id == ARTICLE.source_id
    assert analysis.overall_bias_direction == "pro-Western"
    assert analysis.political_compass is not None
