from __future__ import annotations

from pydantic import BaseModel


class PoliticalCompassPoint(BaseModel):
    economic_axis: float            # -1 (left/statist) to +1 (market/liberal)
    social_axis: float              # -1 (authoritarian) to +1 (libertarian)
    regional_context: str           # why the score is interpreted this way regionally
    label: str                      # short human-readable quadrant/position label
    confidence: float               # 0-1 confidence in the compass placement


class ArticleBiasAnalysis(BaseModel):
    article_url: str
    source_id: str
    overall_bias_direction: str      # e.g. "pro-Western", "pro-BRICS", "neutral"
    confidence: float                # 0–1
    framing_analysis: str            # natural-language explanation of framing
    loaded_terms: list[str]          # politically charged terms with explanations
    omissions: list[str]             # topics covered by others but missing here
    sentiment_score: float           # -1 (very negative) to +1 (very positive)
    attribution_balance: str         # who is quoted and how balanced
    political_compass: PoliticalCompassPoint | None = None


class BiasReport(BaseModel):
    topic: str
    consensus_facts: list[str]               # agreed upon by most sources
    disputed_framings: list[dict]            # {framing, sources_using_it, geopolitical_pattern}
    per_article: list[ArticleBiasAnalysis]
    geopolitical_patterns: list[str]         # high-level cross-source observations
    balanced_summary: str                    # LLM-generated neutral summary
    methodology_note: str                    # transparency about analysis approach
