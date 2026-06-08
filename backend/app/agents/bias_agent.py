from __future__ import annotations

import asyncio
import logging

from app.agents.article_analyzer import _mock_analysis, analyze
from app.agents.comparator import compare
from app.agents.source_profiler import get_source_profile
from app.models.article import Article, ArticleBundle
from app.models.bias_report import ArticleBiasAnalysis, BiasReport
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


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

    async def analyze_article(self, article: Article) -> tuple[ArticleBiasAnalysis, dict]:
        """Analyze one article and return the analysis plus its source profile."""
        source_profile = get_source_profile(article.source_id, self.source_registry)
        try:
            analysis = await analyze(
                article=article,
                source_profile=source_profile,
                llm_service=self.llm_service,
            )
        except Exception as exc:
            logger.warning(
                "Article analysis task failed for %s — using mock fallback: %s: %r",
                article.url,
                type(exc).__name__,
                exc,
            )
            analysis = _mock_analysis(article, source_profile)
        return analysis, source_profile

    async def final_report(
        self,
        *,
        query: str,
        articles: list[Article],
        analyses: list[ArticleBiasAnalysis],
        source_profiles: list[dict],
    ) -> BiasReport:
        """Produce the cross-source report from already streamed analyses."""
        return await compare(
            analyses,
            topic=query,
            llm_service=self.llm_service,
            articles=articles,
            source_profiles=source_profiles,
        )

    async def analyze(self, bundle: ArticleBundle) -> BiasReport:
        """Run the full bias analysis pipeline on an ArticleBundle.

        Returns a BiasReport with per-article analyses and cross-source findings.
        """
        tasks = [self.analyze_article(article) for article in bundle.articles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        analyses: list[ArticleBiasAnalysis] = []
        source_profiles: list[dict] = []
        for article, result in zip(bundle.articles, results):
            if isinstance(result, Exception):
                logger.warning(
                    "Article analysis task failed for %s — using mock fallback: %s: %r",
                    article.url,
                    type(result).__name__,
                    result,
                )
                source_profile = get_source_profile(article.source_id, self.source_registry)
                analyses.append(_mock_analysis(article, source_profile))
                source_profiles.append(source_profile)
            else:
                analysis, source_profile = result
                analyses.append(analysis)
                source_profiles.append(source_profile)
        return await self.final_report(
            query=bundle.query,
            articles=bundle.articles,
            analyses=analyses,
            source_profiles=source_profiles,
        )
