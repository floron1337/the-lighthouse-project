from __future__ import annotations

import json
import logging

from app.agents.prompts import BIAS_COMPARISON_PROMPT
from app.models.bias_report import ArticleBiasAnalysis, BiasReport
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_METHODOLOGY_NOTE = (
    "Bias analysis compares framing, loaded language, omissions, and attribution "
    "patterns across sources with known geopolitical alignments. "
    "Confidence scores are model estimates; results are for informational purposes."
)


def _mock_report(analyses: list[ArticleBiasAnalysis], topic: str) -> BiasReport:
    western = [a.source_id for a in analyses if a.overall_bias_direction == "pro-Western"]
    brics = [a.source_id for a in analyses if a.overall_bias_direction == "pro-BRICS"]
    return BiasReport(
        topic=topic or "Unknown topic",
        consensus_facts=[
            "[Mock] All sources confirm the event occurred and cite official statements.",
            "[Mock] Multiple international actors are mentioned across all sources.",
        ],
        disputed_framings=[
            {
                "framing": "[Mock] Western-aligned sources frame it as a defensive/lawful action",
                "sources_using_it": western,
                "geopolitical_pattern": "NATO/Five Eyes bloc",
            },
            {
                "framing": "[Mock] BRICS-aligned sources frame it as external provocation",
                "sources_using_it": brics,
                "geopolitical_pattern": "BRICS bloc",
            },
        ],
        per_article=analyses,
        geopolitical_patterns=[
            "[Mock] Coverage splits along NATO/BRICS alliance lines.",
            "[Mock] Non-aligned sources adopt a de-escalation or regional-stability framing.",
        ],
        balanced_summary=(
            "[Mock] Multiple international actors are involved in this story. "
            "Sources differ primarily on attribution of responsibility and framing of intent. "
            "A neutral reading suggests ongoing negotiation with unresolved points of contention."
        ),
        methodology_note=_METHODOLOGY_NOTE,
    )


async def compare(
    analyses: list[ArticleBiasAnalysis],
    topic: str = "",
    llm_service: LLMService | None = None,
) -> BiasReport:
    """Produce a cross-source BiasReport from per-article analyses.

    Groups analyses by bias direction, then calls the LLM with
    prompts.BIAS_COMPARISON_PROMPT to generate consensus facts, disputed
    framings, geopolitical patterns, and a balanced summary.

    Args:
        analyses: List of per-article ArticleBiasAnalysis results.
        topic: The original user query, used as the report's topic field.
        llm_service: LLM wrapper; uses mock fallback if None or in mock mode.

    Returns:
        BiasReport with consensus facts, disputed framings, and summary.
    """
    if not analyses:
        return _mock_report(analyses, topic)

    if llm_service is None or llm_service.use_mock:
        return _mock_report(analyses, topic)

    articles_summary = "\n".join(
        f"- [{a.source_id}] Direction: {a.overall_bias_direction} | "
        f"Framing: {a.framing_analysis[:200]} | "
        f"Loaded terms: {', '.join(a.loaded_terms[:5])}"
        for a in analyses
    )

    prompt = BIAS_COMPARISON_PROMPT.format(
        n_sources=len(analyses),
        topic=topic or "unknown topic",
        articles_summary=articles_summary,
    )

    try:
        raw = await llm_service.complete(prompt)
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data: dict = json.loads(cleaned)

        return BiasReport(
            topic=topic or "Unknown topic",
            consensus_facts=data.get("consensus_facts", []),
            disputed_framings=data.get("disputed_framings", []),
            per_article=analyses,
            geopolitical_patterns=data.get("geopolitical_patterns", []),
            balanced_summary=data.get("balanced_summary", ""),
            methodology_note=_METHODOLOGY_NOTE,
        )
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("Comparator LLM parse error: %s — using mock fallback", exc)
        return _mock_report(analyses, topic)
