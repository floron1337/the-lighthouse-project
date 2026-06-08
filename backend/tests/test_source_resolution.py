from __future__ import annotations

import json

import pytest

from app.agents.source_registry import resolve_source_name, resolve_source_name_with_llm


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


class FakeLLMService:
    use_mock = False

    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    async def complete(self, prompt: str, *, json_mode: bool = False) -> str:
        self.calls += 1
        assert json_mode is True
        return json.dumps(self.payload)


@pytest.mark.asyncio
async def test_resolve_source_name_uses_llm_for_high_confidence_unknown_country() -> None:
    llm = FakeLLMService(
        {
            "country_code": "IE",
            "confidence": 0.86,
            "reason": "The outlet is based in Ireland.",
        }
    )

    source_id, country = await resolve_source_name_with_llm(
        "Example Dublin Times",
        registry=REGISTRY,
        llm_service=llm,
        url="https://example-dublin.test/story",
        title="Regional story",
    )

    assert source_id == "example_dublin_times"
    assert country == "IE"
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_resolve_source_name_rejects_low_confidence_llm_country() -> None:
    llm = FakeLLMService(
        {
            "country_code": "IE",
            "confidence": 0.42,
            "reason": "Guessing from the title.",
        }
    )

    source_id, country = await resolve_source_name_with_llm(
        "Example Mystery Outlet",
        registry=REGISTRY,
        llm_service=llm,
        url="https://mystery.test/story",
        title="Regional story",
    )

    assert source_id == "example_mystery_outlet"
    assert country == "XX"


@pytest.mark.asyncio
async def test_resolve_source_name_uses_domain_map_before_llm() -> None:
    llm = FakeLLMService({"country_code": "US", "confidence": 0.99, "reason": "unused"})

    source_id, country = await resolve_source_name_with_llm(
        "Unknown",
        registry=REGISTRY,
        llm_service=llm,
        url="https://www.dw.com/en/story",
        title="Regional story",
    )

    assert source_id == "unknown"
    assert country == "DE"
    assert llm.calls == 0
