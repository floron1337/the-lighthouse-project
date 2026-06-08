from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from app.agents.bias_agent import BiasAnalystAgent
from app.agents.crawler_agent import NewsCrawlerAgent
from app.agents.source_registry import load_registry
from app.models.article import Article
from app.models.bias_report import ArticleBiasAnalysis
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_ANALYSIS_CONCURRENCY = 2


async def process_query(query: str) -> AsyncGenerator[dict[str, Any], None]:
    """Main orchestration pipeline: crawler → bias analyst → streamed SSE events.

    This is the single entry point that chains Agent 1 and Agent 2. The wiring
    here is real (not mocked); only the leaf functions inside each agent are
    stubbed and tagged with their ticket numbers.

    Yields dicts with "type" and "data" keys:
      {"type": "article",     "data": <Article serialized to dict>}  — one per article
      {"type": "bias_report", "data": <BiasReport serialized to dict>} — once at the end
      {"type": "error",       "data": {"message": str}}              — on unhandled failure

    Args:
        query: Raw user query string from the search endpoint.
    """
    registry = load_registry()
    llm = LLMService()

    crawler = NewsCrawlerAgent(source_registry=registry, llm_service=llm)
    analyst = BiasAnalystAgent(source_registry=registry, llm_service=llm)
    semaphore = asyncio.Semaphore(_ANALYSIS_CONCURRENCY)
    articles: list[Article] = []
    analyses: list[ArticleBiasAnalysis] = []
    source_profiles: list[dict] = []
    pending: set[asyncio.Task] = set()

    async def analyze_with_limit(article: Article) -> tuple[ArticleBiasAnalysis, dict]:
        async with semaphore:
            return await analyst.analyze_article(article)

    async def emit_finished_analyses() -> AsyncGenerator[dict[str, Any], None]:
        done = {task for task in pending if task.done()}
        for task in done:
            pending.remove(task)
            analysis, source_profile = task.result()
            analyses.append(analysis)
            source_profiles.append(source_profile)
            yield {"type": "article_analysis", "data": analysis.model_dump(mode="json")}

    try:
        async for article in crawler.iter_articles(query):
            articles.append(article)
            yield {"type": "article", "data": article.model_dump(mode="json")}
            pending.add(asyncio.create_task(analyze_with_limit(article)))
            async for event in emit_finished_analyses():
                yield event
    except Exception as exc:
        logger.exception("Crawler phase failed for query %r: %s", query, exc)
        yield {"type": "error", "data": {"message": f"Crawler failed: {exc}"}}
        return

    for task in asyncio.as_completed(pending):
        analysis, source_profile = await task
        analyses.append(analysis)
        source_profiles.append(source_profile)
        yield {"type": "article_analysis", "data": analysis.model_dump(mode="json")}

    if not articles:
        yield {"type": "error", "data": {"message": "No articles found for this query."}}
        return

    try:
        report = await analyst.final_report(
            query=query,
            articles=articles,
            analyses=analyses,
            source_profiles=source_profiles,
        )
    except Exception as exc:
        logger.exception("Bias analysis phase failed for query %r: %s", query, exc)
        yield {"type": "error", "data": {"message": f"Bias analysis failed: {exc}"}}
        return

    yield {"type": "bias_report", "data": report.model_dump(mode="json")}
