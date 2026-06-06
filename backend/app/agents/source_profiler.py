from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.agents.source_registry import get_source

_PRESS_FREEDOM_PATH = Path(__file__).parent.parent / "press_freedom_index.json"

_UNKNOWN_PROFILE: dict = {
    "source_id": "unknown",
    "name": "Unknown",
    "country": "Unknown",
    "region": "Unknown",
    "ownership": "unknown",
    "known_lean": "unknown",
    "alliance_bloc": "Non-Aligned",
    "credibility_score": 0.5,
    "press_freedom_rank": None,
    "press_freedom_score": None,
    "press_freedom_category": "unknown",
    "editorial_summary": "No source profile is available for this outlet.",
    "regional_context": "Unknown regional media context.",
    "compass_baseline": {
        "economic_axis": 0.0,
        "social_axis": 0.0,
        "label": "Unknown / unprofiled",
        "confidence": 0.25,
    },
}


@lru_cache(maxsize=1)
def _load_press_freedom_index() -> dict[str, dict]:
    with open(_PRESS_FREEDOM_PATH) as f:
        return json.load(f)


def _clamp(value: float, low: float = -1.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _lean_axis(known_lean: str) -> float:
    lean = known_lean.lower()
    if "left" in lean:
        return -0.35
    if "right" in lean:
        return 0.45
    if "pro-kremlin" in lean or "pro-ccp" in lean:
        return -0.15
    return 0.0


def _social_axis(source: dict, press_freedom: dict | None) -> float:
    ownership = source.get("ownership", "").lower()
    lean = source.get("known_lean", "").lower()
    axis = 0.0

    if ownership == "state_funded":
        axis -= 0.2
    elif ownership in {"public_trust", "nonprofit"}:
        axis += 0.15

    if "pro-kremlin" in lean or "pro-ccp" in lean:
        axis -= 0.55

    score = press_freedom.get("score") if press_freedom else None
    if isinstance(score, int | float):
        if score >= 75:
            axis += 0.2
        elif score < 50:
            axis -= 0.3

    return _clamp(axis)


def _compass_baseline(source: dict, press_freedom: dict | None) -> dict:
    economic_axis = _lean_axis(source.get("known_lean", ""))
    social_axis = _social_axis(source, press_freedom)
    confidence = 0.45 + (0.2 if press_freedom else 0.0)
    return {
        "economic_axis": round(_clamp(economic_axis), 2),
        "social_axis": round(social_axis, 2),
        "label": _compass_label(economic_axis, social_axis),
        "confidence": round(confidence, 2),
    }


def _compass_label(economic_axis: float, social_axis: float) -> str:
    economic = "left" if economic_axis < -0.2 else "right" if economic_axis > 0.2 else "centrist"
    social = "libertarian" if social_axis > 0.2 else "authoritarian" if social_axis < -0.2 else "institutional"
    return f"{economic} / {social}"


def _editorial_summary(source: dict) -> str:
    name = source.get("name", "This outlet")
    ownership = source.get("ownership", "unknown ownership")
    lean = source.get("known_lean", "unknown lean")
    bloc = source.get("alliance_bloc", "Non-Aligned")
    return (
        f"{name} is a {ownership.replace('_', ' ')} outlet with a {lean} "
        f"editorial profile, contextualized here against the {bloc} bloc."
    )


def _regional_context(source: dict, press_freedom: dict | None) -> str:
    region = source.get("region", "Unknown region")
    country = source.get("country", "Unknown country")
    bloc = source.get("alliance_bloc", "Non-Aligned")
    category = (press_freedom or {}).get("category", "unknown")
    return (
        f"{country} is treated as part of {region}; the outlet is compared "
        f"within a {bloc} context and a {category} press-freedom environment."
    )


def get_source_profile(source_id: str, registry: list[dict]) -> dict:
    """Build a geopolitical profile for a news source.

    Loads metadata from the registry (country, ownership, known lean, alliance
    bloc, credibility score) and enriches it with press-freedom index data
    (Reporters Without Borders rank keyed by country code) and optionally an
    LLM-derived editorial history summary.

    Args:
        source_id: Registry id (e.g. "bbc_news").
        registry: Loaded source registry list.

    Returns:
        Dict with registry metadata plus press-freedom, editorial, regional,
        and political-compass baseline fields.
    """
    source = get_source(source_id, registry)
    if source is None:
        return {**_UNKNOWN_PROFILE, "source_id": source_id}

    press_freedom = _load_press_freedom_index().get(source.get("country", ""))
    return {
        **source,
        "source_id": source.get("id", source_id),
        "press_freedom_rank": (press_freedom or {}).get("rank"),
        "press_freedom_score": (press_freedom or {}).get("score"),
        "press_freedom_category": (press_freedom or {}).get("category", "unknown"),
        "editorial_summary": _editorial_summary(source),
        "regional_context": _regional_context(source, press_freedom),
        "compass_baseline": _compass_baseline(source, press_freedom),
    }
