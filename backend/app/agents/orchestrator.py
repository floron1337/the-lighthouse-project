from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from app.agents.bias_agent import BiasAnalystAgent
from app.agents.crawler_agent import NewsCrawlerAgent
from app.agents.source_registry import load_registry
from app.services.llm_service import LLMService


async def process_query(query: str) -> AsyncGenerator[dict[str, Any], None]:
    """Main orchestration pipeline: crawler → bias analyst → streamed SSE events.

    This is the single entry point that chains Agent 1 and Agent 2. The wiring
    here is real (not mocked); only the leaf functions inside each agent are
    stubbed and tagged with their ticket numbers.

    Yields dicts with "type" and "data" keys:
      {"type": "article",     "data": <Article serialized to dict>}  — one per article
      {"type": "bias_report", "data": <BiasReport serialized to dict>} — once at the end

    Args:
        query: Raw user query string from the search endpoint.
    """
    registry = load_registry()
    llm = LLMService()

    # Phase 1 — Crawl (THE-7, THE-8, THE-9 implement the leaf functions)
    crawler = NewsCrawlerAgent(source_registry=registry, llm_service=llm)
    bundle = await crawler.search(query)

    for article in bundle.articles:
        yield {"type": "article", "data": article.model_dump(mode="json")}

    # Phase 2 — Bias analysis (THE-10, THE-11, THE-14 implement the leaf functions)
    analyst = BiasAnalystAgent(source_registry=registry, llm_service=llm)
    report = await analyst.analyze(bundle)

    yield {"type": "bias_report", "data": report.model_dump(mode="json")}
