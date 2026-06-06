from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.agents.prompts import BIAS_ANALYSIS_PROMPT
from app.models.article import Article
from app.models.bias_report import ArticleBiasAnalysis, PoliticalCompassPoint
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

# All key variants the model might emit → canonical field name
_KEY_ALIASES: dict[str, str] = {
    "framing": "framing_analysis",
    "Framing": "framing_analysis",
    "tone": "sentiment_score",
    "Tone": "sentiment_score",
    "loaded_language": "loaded_terms",
    "Loaded language": "loaded_terms",
    "Loaded Language": "loaded_terms",
    "attribution": "attribution_balance",
    "Attribution": "attribution_balance",
    "overall bias direction": "overall_bias_direction",
    "Overall bias direction": "overall_bias_direction",
    "Overall Bias Direction": "overall_bias_direction",
    "bias_direction": "overall_bias_direction",
}

def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fallback_direction(source_profile: dict) -> str:
    alliance = source_profile.get("alliance_bloc", "Non-Aligned")
    return _BLOC_TO_DIRECTION.get(alliance, "neutral")


def _default_compass(source_profile: dict) -> PoliticalCompassPoint:
    baseline = source_profile.get("compass_baseline") or {}
    return PoliticalCompassPoint(
        economic_axis=_clamp(float(baseline.get("economic_axis", 0.0)), -1.0, 1.0),
        social_axis=_clamp(float(baseline.get("social_axis", 0.0)), -1.0, 1.0),
        regional_context=source_profile.get(
            "regional_context",
            "No regional context was available for this outlet.",
        ),
        label=str(baseline.get("label", "centrist / institutional")),
        confidence=_clamp(float(baseline.get("confidence", 0.4)), 0.0, 1.0),
    )


def _normalise_compass(data: dict, source_profile: dict) -> dict:
    compass = (
        data.get("political_compass")
        or data.get("political_compass_point")
        or data.get("compass")
        or {}
    )
    if not isinstance(compass, dict):
        compass = {}

    fallback = _default_compass(source_profile)
    economic_axis = compass.get("economic_axis", compass.get("economic", compass.get("x")))
    social_axis = compass.get("social_axis", compass.get("social", compass.get("y")))
    confidence = compass.get("confidence", fallback.confidence)

    return {
        "economic_axis": _clamp(float(economic_axis if economic_axis is not None else fallback.economic_axis), -1.0, 1.0),
        "social_axis": _clamp(float(social_axis if social_axis is not None else fallback.social_axis), -1.0, 1.0),
        "regional_context": str(compass.get("regional_context") or fallback.regional_context),
        "label": str(compass.get("label") or fallback.label),
        "confidence": _clamp(float(confidence), 0.0, 1.0),
    }


def _mock_analysis(article: Article, source_profile: dict) -> ArticleBiasAnalysis:
    alliance = source_profile.get("alliance_bloc", "Non-Aligned")
    lean = source_profile.get("known_lean", "centre")
    bias_direction = _fallback_direction(source_profile)
    return ArticleBiasAnalysis(
        article_url=article.url,
        source_id=article.source_id,
        overall_bias_direction=bias_direction,
        confidence=0.78,
        framing_analysis=(
            f"[Mock] {article.source_name} frames the story from a {lean} editorial "
            f"perspective aligned with the {alliance} bloc."
        ),
        loaded_terms=["[mock term A]", "[mock term B]"],
        omissions=["[mock omission]"],
        sentiment_score=0.0,
        attribution_balance="[Mock] Quotes primarily government officials.",
        political_compass=_default_compass(source_profile),
    )


def _parse_response(raw: str, article: Article, source_profile: dict) -> ArticleBiasAnalysis:
    """Parse LLM JSON into ArticleBiasAnalysis, filling in known fields."""
    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    data: dict = json.loads(cleaned)

    # Flatten if the model wrapped everything under a nested "analysis" key
    if "analysis" in data and isinstance(data["analysis"], dict):
        nested = data.pop("analysis")
        for k, v in nested.items():
            if k not in data:
                data[k] = v

    # Normalise all known key variants to canonical field names
    for alias, canonical in _KEY_ALIASES.items():
        if alias in data and canonical not in data:
            data[canonical] = data.pop(alias)

    # Identity fields always come from the article itself
    data["article_url"] = article.url
    data["source_id"] = article.source_id

    data["overall_bias_direction"] = data.get("overall_bias_direction") or _fallback_direction(source_profile)
    data["framing_analysis"] = data.get("framing_analysis") or "No framing analysis returned by model."
    data["attribution_balance"] = data.get("attribution_balance") or "No attribution analysis returned by model."
    data["confidence"] = _clamp(float(data.get("confidence", 0.70)), 0.0, 1.0)
    data["sentiment_score"] = _clamp(float(data.get("sentiment_score", 0.0)), -1.0, 1.0)
    data["political_compass"] = _normalise_compass(data, source_profile)

    # Ensure list fields are actually lists
    for field in ("loaded_terms", "omissions"):
        if field not in data or not isinstance(data[field], list):
            data[field] = []

    # String field fallbacks so Pydantic never sees a missing required field
    if not data.get("framing_analysis"):
        data["framing_analysis"] = "No framing analysis available."
    if not data.get("attribution_balance"):
        data["attribution_balance"] = "No attribution data available."
    if not data.get("overall_bias_direction"):
        data["overall_bias_direction"] = "neutral"

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
        press_freedom_category=source_profile.get("press_freedom_category", "unknown"),
        regional_context=source_profile.get("regional_context", "unknown regional context"),
        title=article.title,
        full_text=article.full_text[:2000],
    )

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            raw = await llm_service.complete(prompt, json_mode=True)
            if not raw or not raw.strip():
                logger.warning("Empty LLM response for article %s — using mock fallback", article.url)
                return _mock_analysis(article, source_profile)
            return _parse_response(raw, article, source_profile)
        except (json.JSONDecodeError, ValidationError, KeyError, ValueError) as exc:
            logger.warning("Article analysis parse error (attempt %d/%d): %s", attempt, _MAX_RETRIES, exc)

    logger.error("All retries exhausted for article %s — using mock fallback", article.url)
    return _mock_analysis(article, source_profile)
