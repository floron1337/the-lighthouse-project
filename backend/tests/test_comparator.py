from __future__ import annotations

import pytest

from app.agents.comparator import compare
from app.models.bias_report import ArticleBiasAnalysis


class FailingLLMService:
    use_mock = False

    async def complete(self, prompt: str) -> str:
        raise ConnectionError("ollama unavailable")


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


@pytest.mark.asyncio
async def test_compare_falls_back_when_llm_is_unavailable() -> None:
    report = await compare([ANALYSIS], topic="EU AI Act", llm_service=FailingLLMService())

    assert report.topic == "EU AI Act"
    assert report.per_article == [ANALYSIS]
    assert report.balanced_summary
