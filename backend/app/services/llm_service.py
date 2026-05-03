from __future__ import annotations


class LLMService:
    """Wrapper around the Anthropic API for LLM completions.

    In production (use_mock=False), calls Claude via the Anthropic SDK.
    In development / tests (use_mock=True), returns a canned string without
    making any network call.
    """

    def __init__(self, *, use_mock: bool = False) -> None:
        self.use_mock = use_mock
        if not use_mock:
            import os
            import anthropic  # noqa: PLC0415
            self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def complete(self, prompt: str) -> str:
        """Send a prompt to Claude and return the completion as a plain string.

        Args:
            prompt: Full prompt string.

        Returns:
            Model response text.

        Raises:
            NotImplementedError: When use_mock=False (real calls not yet wired).
        """
        if self.use_mock:
            return f"[mock LLM response for: {prompt[:60]}...]"
        # TODO(THE-5): wire real anthropic claude-sonnet-4-6 call with streaming support
        raise NotImplementedError(
            "Real LLM calls are not yet implemented. "
            "Use LLMService(use_mock=True) for development and tests."
        )
