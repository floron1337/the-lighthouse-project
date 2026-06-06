from __future__ import annotations

import json
import logging
import random

from pydantic import ValidationError

from app.agents.prompts import BIAS_ANALYSIS_PROMPT
from app.models.article import Article
from app.models.bias_report import ArticleBiasAnalysis
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_BLOC_TO_DIRECTION: dict[str, str] = {
    "NATO/Five Eyes": "pro-Western",
    "NATO": "pro-Western",
    "G7/Indo-Pacific": "pro-Western",
    "BRICS": "pro-BRICS",
    "BRICS/Non-Aligned": "mixed",
    "Non-Aligned": "neutral",
}

_MAX_RETRIES = 3


def _mock_analysis(article: Article, source_profile: dict) -> ArticleBiasAnalysis:
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
        loaded_terms=["[mock term A]", "[mock term B]"],
        omissions=["[mock omission]"],
        sentiment_score=round(random.uniform(-0.5, 0.5), 2),
        attribution_balance="[Mock] Quotes primarily government officials.",
    )


def _parse_response(raw: str, article: Article, source_profile: dict) -> ArticleBiasAnalysis:
    """Parse LLM JSON into ArticleBiasAnalysis, filling in known fields."""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data: dict = json.loads(cleaned)

    # Normalise field name variants the model might use
    if "tone" in data and "sentiment_score" not in data:
        data["sentiment_score"] = data.pop("tone")
    if "loaded_language" in data and "loaded_terms" not in data:
        data["loaded_terms"] = data.pop("loaded_language")
    if "framing" in data and "framing_analysis" not in data:
        data["framing_analysis"] = data.pop("framing")
    if "attribution" in data and "attribution_balance" not in data:
        data["attribution_balance"] = data.pop("attribution")

    # Always set identity fields from known values
    data["article_url"] = article.url
    data["source_id"] = article.source_id

    # Ensure required numeric fields have sensible defaults
    if "confidence" not in data:
        data["confidence"] = 0.70
    if "sentiment_score" not in data:
        data["sentiment_score"] = 0.0

    # Ensure list fields are actually lists
    for field in ("loaded_terms", "omissions"):
        if field not in data or not isinstance(data[field], list):
            data[field] = []

    return ArticleBiasAnalysis.model_validate(data)


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
    if llm_service is None or llm_service.use_mock:
        return _mock_analysis(article, source_profile)

    prompt = BIAS_ANALYSIS_PROMPT.format(
        source_name=article.source_name,
        country=source_profile.get("country", article.country),
        ownership=source_profile.get("ownership", "unknown"),
        known_lean=source_profile.get("known_lean", "unknown"),
        alliance_bloc=source_profile.get("alliance_bloc", "Non-Aligned"),
        title=article.title,
        full_text=article.full_text[:2000],
    )

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            raw = await llm_service.complete(prompt)
            return _parse_response(raw, article, source_profile)
        except (json.JSONDecodeError, ValidationError, KeyError) as exc:
            logger.warning("Article analysis parse error (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc)

    logger.error("All retries exhausted for article %s — using mock fallback", article.url)
    return _mock_analysis(article, source_profile)
