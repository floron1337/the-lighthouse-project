from __future__ import annotations

import json
import os


class LLMService:
    """Shared LLM wrapper used by both the News Crawler and Bias Analyst agents.

    In development / tests (use_mock=True or LLM_MOCK=true), returns a canned
    string without any network call.  In production, sends the prompt to a local
    Ollama instance via its REST API and returns the generated text.

    Configuration (all optional — defaults work with a stock Ollama install):
        OLLAMA_URL   – base URL of the Ollama daemon  (default: http://localhost:11434)
        OLLAMA_MODEL – model tag to use               (default: llama3.2)
        LLM_MOCK     – set to "true" to force mock mode (default: false)
    """

    def __init__(
        self,
        *,
        use_mock: bool | None = None,
        ollama_url: str | None = None,
        model: str | None = None,
    ) -> None:
        if use_mock is None:
            use_mock = os.getenv("LLM_MOCK", "false").lower() == "true"
        self.use_mock = use_mock
        self._ollama_url = (ollama_url or os.getenv("OLLAMA_URL", "http://localhost:11434")).rstrip("/")
        self._model = model or os.getenv("OLLAMA_MODEL", "llama3.2")

    async def complete(self, prompt: str) -> str:
        """Send *prompt* to Ollama and return the completion as a plain string.

        Uses Ollama's /api/generate endpoint with stream=false so the full
        response arrives in a single JSON object.
        """
        if self.use_mock:
            return f"[mock LLM response for: {prompt[:60]}...]"

        import httpx  # noqa: PLC0415

        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self._ollama_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["response"]
