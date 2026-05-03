from __future__ import annotations

from app.agents.source_registry import get_source

_UNKNOWN_PROFILE: dict = {
    "source_id": "unknown",
    "country": "Unknown",
    "region": "Unknown",
    "ownership": "unknown",
    "known_lean": "unknown",
    "alliance_bloc": "Non-Aligned",
    "credibility_score": 0.5,
    "press_freedom_rank": None,
}


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
        Dict with keys: source_id, country, region, ownership, known_lean,
        alliance_bloc, credibility_score, press_freedom_rank.
    """
    # TODO(THE-10): enrich with RSF press-freedom index API (rsf.org/en/index)
    #               keyed by ISO country code; add LLM editorial history summary
    source = get_source(source_id, registry)
    if source is None:
        return {**_UNKNOWN_PROFILE, "source_id": source_id}
    return {**source, "press_freedom_rank": None}
