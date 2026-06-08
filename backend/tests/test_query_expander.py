from __future__ import annotations

import json

import pytest

import app.agents.query_expander as query_expander
from app.agents.query_expander import expand


class FakeLLMService:
    use_mock = False

    def __init__(self, response: str) -> None:
        self.response = response

    async def complete(self, prompt: str) -> str:
        return self.response


class FailingLLMService:
    use_mock = False

    async def complete(self, prompt: str) -> str:
        raise ConnectionError("ollama unavailable")


class SequenceLLMService:
    use_mock = False

    def __init__(self, responses: list[str | Exception]) -> None:
        self.responses = responses
        self.calls = 0

    async def complete(self, prompt: str) -> str:
        self.calls += 1
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.asyncio
async def test_expand_parses_llm_query_variants() -> None:
    queries = await expand("EU AI Act", FakeLLMService(json.dumps(["EU AI Act", "AI regulation Europe"])))

    assert queries == ["EU AI Act", "AI regulation Europe"]


@pytest.mark.asyncio
async def test_expand_falls_back_when_llm_is_unavailable() -> None:
    queries = await expand("EU AI Act", FailingLLMService())

    assert queries == ["EU AI Act", "EU AI Act 2026", "EU AI Act international"]


@pytest.mark.asyncio
async def test_expand_retries_transient_llm_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(query_expander, "_RETRY_DELAY_SECONDS", 0)
    llm = SequenceLLMService(
        [
            TimeoutError("ollama timed out"),
            json.dumps(["Romania drone blast", "Galati port explosion"]),
        ]
    )

    queries = await expand("Romania Galati drone explosion", llm)

    assert llm.calls == 2
    assert queries == ["Romania drone blast", "Galati port explosion"]


@pytest.mark.asyncio
async def test_expand_retries_malformed_llm_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(query_expander, "_RETRY_DELAY_SECONDS", 0)
    llm = SequenceLLMService(
        [
            "not json",
            json.dumps(["Romania Galati drone explosion", "Romania NATO drone incident"]),
        ]
    )

    queries = await expand("Romania Galati drone explosion", llm)

    assert llm.calls == 2
    assert queries == ["Romania Galati drone explosion", "Romania NATO drone incident"]
