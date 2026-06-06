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
- Press freedom category: {press_freedom_category}
- Regional context: {regional_context}

Article to analyze:
HEADLINE: {title}
TEXT (first 2000 chars): {full_text}

Analyze across these six dimensions:
1. Framing — how does the headline/lede frame the story?
2. Tone — emotional valence; provide a float from -1.0 (very negative) to +1.0 (very positive)
3. Loaded language — list any politically charged terms (return as JSON array of strings)
4. Omissions — what context do other sources typically cover that is absent here?
5. Attribution — who is quoted? Is representation balanced?
6. Overall bias direction — one of: "pro-Western", "pro-BRICS", "pro-government", "neutral", "mixed"
7. Political compass placement — estimate how this article/source framing lands within its regional context:
   - economic_axis: float from -1.0 (left/statist) to +1.0 (market/liberal)
   - social_axis: float from -1.0 (authoritarian/conservative) to +1.0 (libertarian/progressive)
   - regional_context: one sentence explaining the regional comparison
   - label: short label such as "centrist / institutional"
   - confidence: float from 0.0 to 1.0

Respond ONLY as JSON matching ArticleBiasAnalysis (no markdown fences), including:
{{
  "overall_bias_direction": "...",
  "confidence": 0.0,
  "framing_analysis": "...",
  "loaded_terms": [],
  "omissions": [],
  "sentiment_score": 0.0,
  "attribution_balance": "...",
  "political_compass": {{
    "economic_axis": 0.0,
    "social_axis": 0.0,
    "regional_context": "...",
    "label": "...",
    "confidence": 0.0
  }}
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
