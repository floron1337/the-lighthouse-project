from __future__ import annotations

import json
import logging
from inspect import signature

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

_DIRECTION_COMPASS_NUDGES: dict[str, tuple[float, float]] = {
    # These are geopolitical-framing hints, not a party-politics mapping.
    "pro-western": (0.10, 0.04),
    "pro-brics": (-0.10, -0.10),
    "pro-government": (-0.03, -0.16),
    "neutral": (0.0, 0.0),
    "mixed": (0.0, 0.0),
}

_ECONOMIC_RIGHT_TERMS = {
    "business",
    "capital",
    "competition",
    "deregulation",
    "enterprise",
    "growth",
    "investment",
    "investor",
    "market",
    "private",
    "privatization",
    "profit",
    "trade",
}

_ECONOMIC_LEFT_TERMS = {
    "austerity",
    "inequality",
    "labor",
    "nationalization",
    "public",
    "redistribution",
    "regulation",
    "social",
    "state",
    "subsidy",
    "union",
    "welfare",
    "worker",
}

_SOCIAL_AUTHORITARIAN_TERMS = {
    "accusation",
    "alarmism",
    "border",
    "crackdown",
    "deterrence",
    "extremist",
    "military",
    "order",
    "riot",
    "security",
    "sovereignty",
    "stability",
    "terror",
    "threat",
}

_SOCIAL_LIBERTARIAN_TERMS = {
    "accountability",
    "activist",
    "civilian",
    "democracy",
    "dissent",
    "freedom",
    "humanitarian",
    "minority",
    "protest",
    "refugee",
    "rights",
    "transparency",
}

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


async def _complete_json(llm_service: LLMService, prompt: str) -> str:
    if "json_mode" in signature(llm_service.complete).parameters:
        return await llm_service.complete(prompt, json_mode=True)
    return await llm_service.complete(prompt)


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _fallback_direction(source_profile: dict) -> str:
    alliance = source_profile.get("alliance_bloc", "Non-Aligned")
    return _BLOC_TO_DIRECTION.get(alliance, "neutral")


def _compass_label(economic_axis: float, social_axis: float) -> str:
    economic = (
        "left/statist"
        if economic_axis < -0.2
        else "market/liberal"
        if economic_axis > 0.2
        else "centrist"
    )
    social = (
        "libertarian/progressive"
        if social_axis > 0.2
        else "authoritarian/conservative"
        if social_axis < -0.2
        else "institutional"
    )
    return f"{economic} / {social}"


def _contains_any(text: str, terms: set[str]) -> bool:
    text = text.lower()
    return any(term in text for term in terms)


def _keyword_nudge(text: str, positive_terms: set[str], negative_terms: set[str]) -> float:
    nudge = 0.0
    if _contains_any(text, positive_terms):
        nudge += 0.08
    if _contains_any(text, negative_terms):
        nudge -= 0.08
    return nudge


def _direction_nudge(direction: str) -> tuple[float, float]:
    return _DIRECTION_COMPASS_NUDGES.get(direction.lower(), (0.0, 0.0))


def _article_compass_nudges(data: dict) -> tuple[float, float]:
    evidence_text = " ".join(
        [
            str(data.get("framing_analysis", "")),
            " ".join(str(term) for term in data.get("loaded_terms", []) if term),
            " ".join(str(omission) for omission in data.get("omissions", []) if omission),
        ]
    )
    attribution = str(data.get("attribution_balance", "")).lower()

    economic = _keyword_nudge(evidence_text, _ECONOMIC_RIGHT_TERMS, _ECONOMIC_LEFT_TERMS)
    social = _keyword_nudge(
        evidence_text,
        _SOCIAL_LIBERTARIAN_TERMS,
        _SOCIAL_AUTHORITARIAN_TERMS,
    )

    if any(
        marker in attribution
        for marker in ("official", "government", "military", "police")
    ):
        social -= 0.05
    if any(
        marker in attribution
        for marker in ("civilian", "rights", "ngo", "activist", "opposition")
    ):
        social += 0.05

    sentiment = _clamp(float(data.get("sentiment_score", 0.0)), -1.0, 1.0)
    if sentiment < -0.35 and _contains_any(evidence_text, _SOCIAL_AUTHORITARIAN_TERMS):
        social -= 0.04
    elif sentiment > 0.35 and _contains_any(evidence_text, _SOCIAL_LIBERTARIAN_TERMS):
        social += 0.04

    direction_economic, direction_social = _direction_nudge(
        str(data.get("overall_bias_direction", ""))
    )
    return economic + direction_economic, social + direction_social


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
    economic_nudge, social_nudge = _article_compass_nudges(data)
    adjusted_economic = (
        float(economic_axis if economic_axis is not None else fallback.economic_axis)
        + economic_nudge
    )
    adjusted_social = (
        float(social_axis if social_axis is not None else fallback.social_axis)
        + social_nudge
    )
    adjusted_confidence = _clamp(float(confidence), 0.0, 1.0)
    if data.get("framing_analysis") or data.get("loaded_terms") or data.get("omissions"):
        adjusted_confidence = _clamp(adjusted_confidence + 0.05, 0.0, 1.0)
    regional_context = str(compass.get("regional_context") or fallback.regional_context)
    if "article framing" not in regional_context.lower():
        regional_context = (
            f"{regional_context} Compass placement is adjusted using article framing, "
            "loaded terms, omissions, attribution, sentiment, and bias direction."
        )

    return {
        "economic_axis": round(_clamp(adjusted_economic, -1.0, 1.0), 2),
        "social_axis": round(_clamp(adjusted_social, -1.0, 1.0), 2),
        "regional_context": regional_context,
        "label": _compass_label(adjusted_economic, adjusted_social),
        "confidence": adjusted_confidence,
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
            raw = await _complete_json(llm_service, prompt)
            if not raw or not raw.strip():
                logger.warning("Empty LLM response for article %s — using mock fallback", article.url)
                return _mock_analysis(article, source_profile)
            return _parse_response(raw, article, source_profile)
        except (json.JSONDecodeError, ValidationError, KeyError, OSError, ValueError) as exc:
            logger.warning(
                "Article analysis failed (attempt %d/%d): %s: %r",
                attempt,
                _MAX_RETRIES,
                type(exc).__name__,
                exc,
            )
        except Exception as exc:
            logger.warning(
                "Article analysis LLM unavailable (attempt %d/%d): %s: %r",
                attempt,
                _MAX_RETRIES,
                type(exc).__name__,
                exc,
            )

    logger.error("All retries exhausted for article %s — using mock fallback", article.url)
    return _mock_analysis(article, source_profile)
