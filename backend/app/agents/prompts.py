from __future__ import annotations

QUERY_EXPANSION_PROMPT = """\
You are a search query optimizer for a bias-aware news aggregation system.

User topic: "{query}"

Generate exactly 3 diverse search sub-queries that together maximize coverage:
1. The precise topic with key named entities
2. A regional or geopolitical angle (e.g. reactions, international perspective)
3. A temporal variant including the year 2026

Output ONLY a JSON array of 3 strings. No explanation, no markdown fences.
Example: ["EU AI Act 2026", "European AI regulation tech industry impact", "EU artificial intelligence law global reaction 2026"]
"""

BIAS_ANALYSIS_PROMPT = """\
You are an expert in media bias and geopolitical framing analysis.

Source context:
- Outlet: {source_name}
- Country: {country}
- Ownership: {ownership}
- Known lean: {known_lean}
- Alliance bloc: {alliance_bloc}

Article to analyze:
HEADLINE: {title}
TEXT (first 2000 chars): {full_text}

Respond ONLY with a flat JSON object using exactly these keys (no nesting, no markdown fences):
{{
  "overall_bias_direction": "<one of: pro-Western | pro-BRICS | pro-government | neutral | mixed>",
  "confidence": <float 0.0–1.0>,
  "framing_analysis": "<how headline/lede frames the story>",
  "sentiment_score": <float -1.0 to +1.0>,
  "loaded_terms": ["<charged term 1>", "<charged term 2>"],
  "omissions": ["<missing context 1>"],
  "attribution_balance": "<who is quoted and whether representation is balanced>"
}}
"""

BIAS_COMPARISON_PROMPT = """\
You are comparing {n_sources} news articles covering the same topic: "{topic}"

Per-source summaries:
{articles_summary}

Identify and return ONLY JSON (no markdown fences) with these keys:
- consensus_facts: list[str] — facts reported by 3+ sources
- disputed_framings: list[dict] — each has "framing", "sources_using_it" (list), "geopolitical_pattern"
- geopolitical_patterns: list[str] — high-level framing observations per alliance bloc
- balanced_summary: str — a neutral 3-sentence summary of the story
"""
