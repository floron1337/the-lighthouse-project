from __future__ import annotations

import asyncio

from app.agents.article_analyzer import analyze
from app.agents.comparator import compare
from app.agents.source_profiler import get_source_profile
from app.models.article import ArticleBundle
from app.models.bias_report import BiasReport
from app.services.llm_service import LLMService


class BiasAnalystAgent:
    """Agent 2 — analyzes articles for geopolitical bias and produces a BiasReport.

    Orchestrates: per-source profiling → per-article analysis (in parallel) →
    cross-source comparison → BiasReport output.

    The leaf functions (get_source_profile, analyze, compare) are stubbed;
    this class wires them together in the real async pipeline.
    """

    def __init__(self, source_registry: list[dict], llm_service: LLMService) -> None:
        self.source_registry = source_registry
        self.llm_service = llm_service

    async def analyze(self, bundle: ArticleBundle) -> BiasReport:
        """Run the full bias analysis pipeline on an ArticleBundle.

        Returns a BiasReport with per-article analyses and cross-source findings.
        """
        tasks = [
            analyze(
                article=article,
                source_profile=get_source_profile(article.source_id, self.source_registry),
                llm_service=self.llm_service,
            )
            for article in bundle.articles
        ]
        analyses = list(await asyncio.gather(*tasks))
        return await compare(analyses, topic=bundle.query, llm_service=self.llm_service)
