from __future__ import annotations

import json
import logging

from app.agents.prompts import QUERY_EXPANSION_PROMPT

logger = logging.getLogger(__name__)
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
    _fallback = [query, f"{query} 2026", f"{query} international"]

    if llm_service is None or llm_service.use_mock:
        return _fallback

    prompt = QUERY_EXPANSION_PROMPT.format(query=query)
    try:
        raw = await llm_service.complete(prompt)
    except Exception as exc:
        logger.warning("Query expansion LLM call failed: %s — using fallback queries", exc)
        return _fallback

    try:
        # Strip any accidental markdown fences the model may add
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        sub_queries: list[str] = json.loads(cleaned)
        if not isinstance(sub_queries, list) or not sub_queries:
            raise ValueError("expected non-empty list")
        return [str(q) for q in sub_queries]
    except (json.JSONDecodeError, ValueError):
        return _fallback
