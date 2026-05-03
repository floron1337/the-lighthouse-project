from __future__ import annotations

import random

from app.models.article import Article
from app.models.bias_report import ArticleBiasAnalysis
from app.services.llm_service import LLMService

_BLOC_TO_DIRECTION: dict[str, str] = {
    "NATO/Five Eyes": "pro-Western",
    "NATO": "pro-Western",
    "G7/Indo-Pacific": "pro-Western",
    "BRICS": "pro-BRICS",
    "BRICS/Non-Aligned": "mixed",
    "Non-Aligned": "neutral",
}


async def analyze(
    article: Article,
    source_profile: dict,
    llm_service: LLMService | None = None,
) -> ArticleBiasAnalysis:
    """Analyze a single article for geopolitical bias across six dimensions.

    Uses an LLM with prompts.BIAS_ANALYSIS_PROMPT to examine framing, tone,
    loaded language, omissions, source attribution, and causal framing. The
    source_profile provides geopolitical context to determine the likely bias
    direction (e.g. "pro-Western", "pro-BRICS", "neutral").

    Args:
        article: The article to analyze.
        source_profile: Enriched geopolitical profile from source_profiler.
        llm_service: LLM wrapper; must not be None in production.

    Returns:
        ArticleBiasAnalysis with scores and natural-language explanations.
    """
    # TODO(THE-11): replace mock with structured LLM call using prompts.BIAS_ANALYSIS_PROMPT;
    #               parse JSON response into ArticleBiasAnalysis; add retry on malformed JSON
    alliance = source_profile.get("alliance_bloc", "Non-Aligned")
    lean = source_profile.get("known_lean", "centre")
    bias_direction = _BLOC_TO_DIRECTION.get(alliance, "neutral")

    return ArticleBiasAnalysis(
        article_url=article.url,
        source_id=article.source_id,
        overall_bias_direction=bias_direction,
        confidence=round(random.uniform(0.60, 0.95), 2),
        framing_analysis=(
            f"[Mock] {article.source_name} frames the story from a {lean} editorial "
            f"perspective aligned with the {alliance} bloc."
        ),
        loaded_terms=["[mock term A — see THE-11]", "[mock term B — see THE-11]"],
        omissions=["[mock omission — implement in THE-11]"],
        sentiment_score=round(random.uniform(-0.5, 0.5), 2),
        attribution_balance="[Mock] Quotes primarily government officials. See THE-11.",
    )
