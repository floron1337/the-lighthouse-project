from __future__ import annotations

from app.agents.source_registry import resolve_source_name


REGISTRY = [
    {"id": "rt", "name": "RT", "country": "RU"},
    {"id": "dw", "name": "Deutsche Welle", "country": "DE"},
    {"id": "aljazeera", "name": "Al Jazeera", "country": "QA"},
]


def test_resolve_source_name_does_not_match_short_name_inside_unrelated_source() -> None:
    source_id, country = resolve_source_name("Fortune", registry=REGISTRY)

    assert source_id == "fortune"
    assert country == "US"


def test_resolve_source_name_uses_aliases_for_common_api_variants() -> None:
    source_id, country = resolve_source_name("DW (English)", registry=REGISTRY)

    assert source_id == "dw"
    assert country == "DE"


def test_resolve_source_name_prefers_explicit_fallback_country() -> None:
    source_id, country = resolve_source_name("Unknown Local Outlet", country="RO", registry=REGISTRY)

    assert source_id == "unknown_local_outlet"
    assert country == "RO"
