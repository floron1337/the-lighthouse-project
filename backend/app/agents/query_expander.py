from __future__ import annotations

from app.services.llm_service import LLMService


async def expand(query: str, llm_service: LLMService | None = None) -> list[str]:
    """Expand a user query into multiple search sub-queries for broader coverage.

    Uses an LLM to produce 3 search variants covering different angles of the
    topic: precise phrasing, regional/geopolitical perspective, and temporal
    context. The sub-queries are searched in parallel across all news APIs.

    Args:
        query: The raw user query string.
        llm_service: LLM wrapper used for expansion; must not be None in prod.

    Returns:
        List of 3–5 sub-query strings.
    """
    # TODO(THE-7): replace mock with LLM-based expansion using llm_service.complete()
    #              and prompts.QUERY_EXPANSION_PROMPT; parse the JSON array response
    return [
        query,
        f"{query} latest news 2026",
        f"{query} international reaction",
    ]
