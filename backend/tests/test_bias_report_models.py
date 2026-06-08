from __future__ import annotations

from app.models.bias_report import ArticleBiasAnalysis, PoliticalCompassPoint


def test_article_bias_analysis_accepts_political_compass() -> None:
    analysis = ArticleBiasAnalysis(
        article_url="https://example.com/article",
        source_id="example",
        overall_bias_direction="neutral",
        confidence=0.8,
        framing_analysis="Balanced framing.",
        loaded_terms=[],
        omissions=[],
        sentiment_score=0.0,
        attribution_balance="Quotes multiple sides.",
        political_compass=PoliticalCompassPoint(
            economic_axis=0.0,
            social_axis=0.1,
            regional_context="Compared within a regional media context.",
            label="centrist / institutional",
            confidence=0.7,
        ),
    )

    assert analysis.political_compass is not None
    assert analysis.political_compass.label == "centrist / institutional"


def test_article_bias_analysis_keeps_compass_optional() -> None:
    analysis = ArticleBiasAnalysis(
        article_url="https://example.com/article",
        source_id="example",
        overall_bias_direction="neutral",
        confidence=0.8,
        framing_analysis="Balanced framing.",
        loaded_terms=[],
        omissions=[],
        sentiment_score=0.0,
        attribution_balance="Quotes multiple sides.",
    )

    assert analysis.political_compass is None
