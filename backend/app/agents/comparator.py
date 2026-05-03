from __future__ import annotations

from app.models.bias_report import ArticleBiasAnalysis, BiasReport


def compare(analyses: list[ArticleBiasAnalysis], topic: str = "") -> BiasReport:
    """Produce a cross-source BiasReport from per-article analyses.

    Groups analyses by alliance_bloc, identifies consensus facts (events
    reported by 3+ sources), surfaces disputed framings (same event described
    differently by different blocs), and calls the LLM with
    prompts.BIAS_COMPARISON_PROMPT to generate the balanced_summary.

    Args:
        analyses: List of per-article ArticleBiasAnalysis results.
        topic: The original user query, used as the report's topic field.

    Returns:
        BiasReport with consensus facts, disputed framings, and summary.
    """
    # TODO(THE-14): implement real comparison — group by alliance_bloc, compute
    #               framing clusters, find consensus facts via string/embedding overlap,
    #               call LLM for balanced_summary using prompts.BIAS_COMPARISON_PROMPT
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
            "[Mock] Coverage splits along NATO/BRICS alliance lines. See THE-14.",
            "[Mock] Non-aligned sources adopt a de-escalation or regional-stability framing.",
        ],
        balanced_summary=(
            "[Mock] Multiple international actors are involved in this story. "
            "Sources differ primarily on attribution of responsibility and framing of intent. "
            "A neutral reading suggests ongoing negotiation with unresolved points of contention."
        ),
        methodology_note=(
            "Bias analysis compares framing, loaded language, omissions, and attribution "
            "patterns across sources with known geopolitical alignments. "
            "Confidence scores are model estimates; results are for informational purposes."
        ),
    )
