from __future__ import annotations

from app.agents.source_profiler import get_source_profile


REGISTRY = [
    {
        "id": "bbc_news",
        "name": "BBC News",
        "country": "GB",
        "region": "Western Europe",
        "ownership": "state_funded",
        "known_lean": "centre",
        "alliance_bloc": "NATO/Five Eyes",
        "rss_url": "http://feeds.bbci.co.uk/news/rss.xml",
        "language": "en",
        "credibility_score": 0.85,
    }
]


def test_get_source_profile_enriches_known_source() -> None:
    profile = get_source_profile("bbc_news", REGISTRY)

    assert profile["source_id"] == "bbc_news"
    assert profile["press_freedom_rank"] is not None
    assert profile["press_freedom_score"] is not None
    assert profile["press_freedom_category"] != "unknown"
    assert "BBC News" in profile["editorial_summary"]
    assert "Western Europe" in profile["regional_context"]
    assert profile["compass_baseline"]["label"]


def test_get_source_profile_handles_unknown_source() -> None:
    profile = get_source_profile("missing_source", REGISTRY)

    assert profile["source_id"] == "missing_source"
    assert profile["country"] == "Unknown"
    assert profile["press_freedom_rank"] is None
    assert profile["compass_baseline"]["confidence"] == 0.25
