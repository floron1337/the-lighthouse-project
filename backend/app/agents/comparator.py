from __future__ import annotations

from collections import Counter, defaultdict
import json
import logging
import re
from inspect import signature

from app.agents.prompts import BIAS_COMPARISON_PROMPT
from app.models.article import Article
from app.models.bias_report import ArticleBiasAnalysis, BiasReport
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

_METHODOLOGY_NOTE = (
    "Bias analysis combines deterministic cross-source comparison with LLM-assisted "
    "interpretation. Consensus facts are clustered from article text; disputed "
    "framings are grouped from per-article analyses, loaded terms, omissions, "
    "attribution patterns, source profiles, and geopolitical alignments. "
    "Confidence scores are model estimates; results are for informational purposes."
)

_STOPWORDS = {
    "about",
    "after",
    "also",
    "amid",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "more",
    "new",
    "of",
    "on",
    "or",
    "over",
    "said",
    "says",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
}


async def _complete_json(llm_service: LLMService, prompt: str) -> str:
    if "json_mode" in signature(llm_service.complete).parameters:
        return await llm_service.complete(prompt, json_mode=True)
    return await llm_service.complete(prompt)


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z][a-zA-Z'-]{2,}", text.lower())
        if token not in _STOPWORDS
    }


def _split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [
        re.sub(r"\s+", " ", piece).strip(" \t\r\n\"'")
        for piece in pieces
        if 40 <= len(piece.strip()) <= 260
    ]


def _source_name(source_id: str, articles_by_source: dict[str, Article]) -> str:
    article = articles_by_source.get(source_id)
    return article.source_name if article else source_id


def _article_for_analysis(
    analysis: ArticleBiasAnalysis,
    articles_by_url: dict[str, Article],
    articles_by_source: dict[str, Article],
) -> Article | None:
    return articles_by_url.get(analysis.article_url) or articles_by_source.get(analysis.source_id)


def _profile_label(source_ids: list[str], source_profiles_by_id: dict[str, dict]) -> str:
    blocs = Counter(
        source_profiles_by_id.get(source_id, {}).get("alliance_bloc", "unknown")
        for source_id in source_ids
    )
    regions = Counter(
        source_profiles_by_id.get(source_id, {}).get("region", "unknown")
        for source_id in source_ids
    )
    bloc = blocs.most_common(1)[0][0] if blocs else "unknown bloc"
    region = regions.most_common(1)[0][0] if regions else "unknown region"
    return f"{bloc} / {region}"


def _top_terms(texts: list[str], limit: int = 5) -> list[str]:
    counts: Counter[str] = Counter()
    for text in texts:
        counts.update(_tokens(text))
    return [term for term, _ in counts.most_common(limit)]


def _confidence_average(analyses: list[ArticleBiasAnalysis]) -> float:
    if not analyses:
        return 0.0
    return round(sum(a.confidence for a in analyses) / len(analyses), 2)


def _sentiment_average(analyses: list[ArticleBiasAnalysis]) -> float:
    if not analyses:
        return 0.0
    return round(sum(a.sentiment_score for a in analyses) / len(analyses), 2)


def _consensus_facts(articles: list[Article], topic: str) -> list[str]:
    candidates: list[dict] = []
    for article in articles:
        for sentence in [article.title, *_split_sentences(article.full_text)]:
            token_set = _tokens(sentence)
            if len(token_set) < 4:
                continue
            candidates.append(
                {
                    "text": sentence.rstrip(".") + ".",
                    "source_id": article.source_id,
                    "tokens": token_set,
                }
            )

    clusters: list[dict] = []
    for candidate in candidates:
        best_cluster: dict | None = None
        best_score = 0.0
        for cluster in clusters:
            overlap = candidate["tokens"] & cluster["tokens"]
            union = candidate["tokens"] | cluster["tokens"]
            score = len(overlap) / max(len(union), 1)
            if len(overlap) >= 4 and score > best_score:
                best_cluster = cluster
                best_score = score

        if best_cluster is None or best_score < 0.24:
            clusters.append(
                {
                    "tokens": set(candidate["tokens"]),
                    "items": [candidate],
                    "sources": {candidate["source_id"]},
                }
            )
        else:
            best_cluster["tokens"].update(candidate["tokens"])
            best_cluster["items"].append(candidate)
            best_cluster["sources"].add(candidate["source_id"])

    total_sources = len({article.source_id for article in articles})
    threshold = 3 if total_sources >= 3 else max(1, total_sources)
    ranked = sorted(
        clusters,
        key=lambda cluster: (len(cluster["sources"]), len(cluster["items"])),
        reverse=True,
    )

    facts: list[str] = []
    for cluster in ranked:
        if len(cluster["sources"]) < threshold:
            continue
        representative = min(cluster["items"], key=lambda item: len(item["text"]))["text"]
        facts.append(f"Reported by {len(cluster['sources'])} sources: {representative}")
        if len(facts) == 5:
            break

    if facts:
        return facts

    if articles:
        return [
            (
                f"Coverage of {topic or 'this topic'} is fragmented: no specific factual "
                "claim appeared across enough sources to meet the consensus threshold."
            )
        ]
    return [f"No article text was available to derive consensus facts for {topic or 'this topic'}."]


def _disputed_framings(
    analyses: list[ArticleBiasAnalysis],
    articles_by_source: dict[str, Article],
    source_profiles_by_id: dict[str, dict],
) -> list[dict]:
    by_direction: dict[str, list[ArticleBiasAnalysis]] = defaultdict(list)
    for analysis in analyses:
        by_direction[analysis.overall_bias_direction].append(analysis)

    framings: list[dict] = []
    for direction, grouped in sorted(by_direction.items(), key=lambda item: len(item[1]), reverse=True):
        source_ids = [analysis.source_id for analysis in grouped]
        source_names = [_source_name(source_id, articles_by_source) for source_id in source_ids]
        term_inputs = [
            analysis.framing_analysis
            + " "
            + " ".join(analysis.loaded_terms)
            + " "
            + " ".join(analysis.omissions)
            for analysis in grouped
        ]
        terms = _top_terms(term_inputs, limit=4)
        if terms:
            emphasis = ", ".join(terms)
            framing = f"{direction} sources emphasize {emphasis}."
        else:
            framing = grouped[0].framing_analysis

        framings.append(
            {
                "framing": framing,
                "sources_using_it": source_names,
                "geopolitical_pattern": _profile_label(source_ids, source_profiles_by_id),
                "confidence": _confidence_average(grouped),
                "sentiment_score": _sentiment_average(grouped),
            }
        )

    return framings[:6]


def _geopolitical_patterns(
    analyses: list[ArticleBiasAnalysis],
    articles_by_source: dict[str, Article],
    source_profiles_by_id: dict[str, dict],
) -> list[str]:
    by_bloc: dict[str, list[ArticleBiasAnalysis]] = defaultdict(list)
    for analysis in analyses:
        bloc = source_profiles_by_id.get(analysis.source_id, {}).get(
            "alliance_bloc",
            analysis.overall_bias_direction,
        )
        by_bloc[bloc].append(analysis)

    patterns: list[str] = []
    for bloc, grouped in sorted(by_bloc.items(), key=lambda item: len(item[1]), reverse=True):
        directions = Counter(a.overall_bias_direction for a in grouped)
        dominant_direction = directions.most_common(1)[0][0]
        source_names = [
            _source_name(analysis.source_id, articles_by_source)
            for analysis in grouped
        ]
        patterns.append(
            (
                f"{bloc} sources ({', '.join(source_names)}) lean mostly "
                f"{dominant_direction}, with average confidence "
                f"{_confidence_average(grouped)} and average sentiment "
                f"{_sentiment_average(grouped)}."
            )
        )

    omitted = Counter(
        omission
        for analysis in analyses
        for omission in analysis.omissions
        if omission and not omission.startswith("[mock")
    )
    if omitted:
        omission, count = omitted.most_common(1)[0]
        patterns.append(f"Most repeated omission theme ({count} sources): {omission}")

    compass_points = [a.political_compass for a in analyses if a.political_compass is not None]
    if compass_points:
        economic = round(sum(p.economic_axis for p in compass_points) / len(compass_points), 2)
        social = round(sum(p.social_axis for p in compass_points) / len(compass_points), 2)
        patterns.append(
            f"Political compass average across analyzed coverage: economic {economic}, social {social}."
        )

    return patterns[:6] or ["No geopolitical pattern could be derived from the available analyses."]


def _balanced_summary(
    topic: str,
    consensus_facts: list[str],
    disputed_framings: list[dict],
    geopolitical_patterns: list[str],
) -> str:
    framing_summary = ""
    if disputed_framings:
        framing_summary = (
            " The main framing divide is: "
            + "; ".join(f["framing"] for f in disputed_framings[:3])
        )
    return (
        f"Across the sampled coverage of {topic or 'this topic'}, the strongest shared basis is "
        f"{consensus_facts[0] if consensus_facts else 'limited by fragmented reporting'}."
        f"{framing_summary} A balanced reading should separate the reported event from each "
        f"source's attribution choices, omissions, and geopolitical context. "
        f"{geopolitical_patterns[0] if geopolitical_patterns else ''}"
    ).strip()


def _is_useful_fact(fact: object, topic: str) -> bool:
    if not isinstance(fact, str):
        return False
    text = re.sub(r"\s+", " ", fact).strip()
    if len(text) < 35:
        return False
    if text.casefold().rstrip(".") == topic.casefold().strip().rstrip("."):
        return False
    return len(_tokens(text)) >= 5


def _valid_llm_framings(framings: object) -> list[dict]:
    if not isinstance(framings, list):
        return []
    valid: list[dict] = []
    for framing in framings:
        if not isinstance(framing, dict):
            continue
        text = framing.get("framing")
        sources = framing.get("sources_using_it")
        pattern = framing.get("geopolitical_pattern")
        if not isinstance(text, str) or len(text.strip()) < 30:
            continue
        if not isinstance(sources, list) or not sources:
            continue
        valid.append(
            {
                "framing": text.strip(),
                "sources_using_it": [str(source) for source in sources],
                "geopolitical_pattern": str(pattern or "Not specified"),
            }
        )
    return valid


def _computed_report(
    analyses: list[ArticleBiasAnalysis],
    topic: str,
    articles: list[Article] | None = None,
    source_profiles: list[dict] | None = None,
) -> BiasReport:
    articles = articles or []
    articles_by_source = {article.source_id: article for article in articles}
    articles_by_url = {article.url: article for article in articles}
    source_profiles_by_id = {
        profile.get("source_id", profile.get("id", "")): profile
        for profile in (source_profiles or [])
    }
    consensus_facts = _consensus_facts(articles, topic)
    disputed_framings = _disputed_framings(analyses, articles_by_source, source_profiles_by_id)
    geopolitical_patterns = _geopolitical_patterns(analyses, articles_by_source, source_profiles_by_id)

    return BiasReport(
        topic=topic or "Unknown topic",
        consensus_facts=consensus_facts,
        disputed_framings=disputed_framings,
        per_article=analyses,
        geopolitical_patterns=geopolitical_patterns,
        balanced_summary=_balanced_summary(
            topic,
            consensus_facts,
            disputed_framings,
            geopolitical_patterns,
        ),
        methodology_note=_METHODOLOGY_NOTE,
    )


async def compare(
    analyses: list[ArticleBiasAnalysis],
    topic: str = "",
    llm_service: LLMService | None = None,
    articles: list[Article] | None = None,
    source_profiles: list[dict] | None = None,
) -> BiasReport:
    """Produce a cross-source BiasReport from per-article analyses.

    Clusters article text into consensus facts, groups per-article framing
    analyses into disputed framings, derives geopolitical patterns from source
    profiles, then optionally asks the LLM to refine the computed report.

    Args:
        analyses: List of per-article ArticleBiasAnalysis results.
        topic: The original user query, used as the report's topic field.
        llm_service: LLM wrapper; uses deterministic output if None or in mock mode.
        articles: Original articles, used for consensus-fact clustering.
        source_profiles: Source profiles, used for geopolitical grouping.

    Returns:
        BiasReport with consensus facts, disputed framings, and summary.
    """
    if not analyses:
        return _computed_report(analyses, topic, articles, source_profiles)

    computed = _computed_report(analyses, topic, articles, source_profiles)

    if llm_service is None or llm_service.use_mock:
        return computed

    articles = articles or []
    articles_by_source = {article.source_id: article for article in articles}
    articles_by_url = {article.url: article for article in articles}

    articles_summary_lines: list[str] = []
    for analysis in analyses:
        article = _article_for_analysis(analysis, articles_by_url, articles_by_source)
        source_name = article.source_name if article else analysis.source_id
        title = article.title if article else "Unknown headline"
        articles_summary_lines.append(
            f"- Source: {source_name} [{analysis.source_id}] | "
            f"Headline: {title[:180]} | "
            f"Direction: {analysis.overall_bias_direction} | "
            f"Framing: {analysis.framing_analysis[:260]} | "
            f"Loaded terms: {', '.join(analysis.loaded_terms[:5]) or 'none'}"
        )
    articles_summary = "\n".join(articles_summary_lines)

    prompt = BIAS_COMPARISON_PROMPT.format(
        n_sources=len(analyses),
        topic=topic or "unknown topic",
        articles_summary=articles_summary,
    )

    try:
        raw = await _complete_json(llm_service, prompt)
    except Exception as exc:
        logger.error("Comparator LLM unavailable: %s: %r — using computed fallback", type(exc).__name__, exc)
        return computed

    try:
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data: dict = json.loads(cleaned)

        llm_facts = [
            str(fact).strip()
            for fact in data.get("consensus_facts", [])
            if _is_useful_fact(fact, topic)
        ]
        llm_framings = _valid_llm_framings(data.get("disputed_framings"))
        llm_patterns = [
            str(pattern).strip()
            for pattern in data.get("geopolitical_patterns", [])
            if isinstance(pattern, str) and len(pattern.strip()) >= 35
        ]
        llm_summary = data.get("balanced_summary")

        return BiasReport(
            topic=topic or "Unknown topic",
            consensus_facts=llm_facts or computed.consensus_facts,
            disputed_framings=llm_framings or computed.disputed_framings,
            per_article=analyses,
            geopolitical_patterns=llm_patterns or computed.geopolitical_patterns,
            balanced_summary=(
                llm_summary.strip()
                if isinstance(llm_summary, str) and len(llm_summary.strip()) >= 20
                else computed.balanced_summary
            ),
            methodology_note=_METHODOLOGY_NOTE,
        )
    except (json.JSONDecodeError, KeyError) as exc:
        logger.error("Comparator LLM parse error: %s: %r — using computed fallback", type(exc).__name__, exc)
        return computed
