# The Lighthouse — AI Agent Architecture Design

## Overview

This document describes the architecture for a bias-aware news aggregator with **two embedded AI agents**:

1. **News Crawler Agent** — given a user query, expands it into sub-queries, searches multiple international news APIs in parallel, extracts article text, and deduplicates results.
2. **Bias Analyst Agent** — receives the crawled articles, runs per-article bias analysis via LLM, then produces a comparative cross-source bias report.

The agents are not bolt-on features — they are **core to the app's data flow**. Every user query triggers both agents in sequence as part of the app's streaming pipeline.

---

## High-Level Data Flow

```
┌──────────────┐
│  User Query  │  e.g. "Russia-Ukraine ceasefire talks"
└──────┬───────┘
       │ POST /api/search
       ▼
┌──────────────────────────────────────────┐
│       AGENT 1: News Crawler              │
│                                          │
│  1. LLM expands query → sub-queries      │
│  2. Parallel search: NewsAPI + GNews     │
│  3. trafilatura extracts full text       │
│  4. TF-IDF cosine deduplication          │
│  5. Streams articles one by one          │
│                                          │
│  Yields: Article events (SSE)            │
└──────────────────┬───────────────────────┘
                   │ article_analysis events (streamed)
                   ▼
┌──────────────────────────────────────────┐
│       AGENT 2: Bias Analyst              │
│                                          │
│  1. Per-article LLM analysis             │
│     (concurrency = 2, semaphore-limited) │
│  2. Streams article_analysis events      │
│     as each LLM call completes           │
│  3. Cross-source comparison via LLM +    │
│     deterministic clustering fallback    │
│                                          │
│  Yields: article_analysis + bias_report  │
└──────────────────┬───────────────────────┘
                   │ [DONE]
                   ▼
┌──────────────────────────────────────────┐
│              Frontend (Next.js)          │
│                                          │
│  - Article cards streamed in real-time   │
│  - Bias badges appear per article        │
│  - World map coloured by source country  │
│  - Country-click filter                  │
│  - Comparative bias report panel         │
│  - Cancel button during crawl/analysis   │
└──────────────────────────────────────────┘
```

---

## Agent 1: News Crawler Agent

### Purpose
Given a user's natural-language prompt, this agent autonomously finds relevant news articles from **diverse international sources** and streams them to the frontend as they are discovered.

### How It Works

#### Step 1 — Query Expansion
`query_expander.py` calls the local LLM (Ollama) with the user's raw query and asks it to generate up to 3 search sub-queries designed to maximize source diversity. On any LLM error the expander falls back to `[query, "{query} 2026", "{query} international"]`.

#### Step 2 — Parallel Multi-Source Search
For each sub-query, the crawler fires requests to two REST APIs concurrently:

| Source | Endpoint | Key |
|---|---|---|
| NewsAPI.org | `/v2/everything` | `NEWSAPI_KEY` env var |
| GNews | `/api/v4/search` | `GNEWS_KEY` env var |

Both searchers apply query sanitization (strip quotes/apostrophes that cause API 400s), honour rate-limit cooldowns, and resolve each article's source to an ISO 3166-1 alpha-2 country code via a two-step lookup:
1. Exact/partial match against `source_registry.json`
2. Substring match against the fallback map in `searchers/_source_map.py` (~120 outlet name fragments → country codes, EU-specific entries listed first to avoid false US matches for "Politico Europe")

If neither key is configured the searchers return empty lists and the agent falls back to mock articles (only when `LLM_MOCK=true`).

#### Step 3 — Extraction & Deduplication
`extractor.py` processes the raw article list in two passes:
1. **Text extraction** — if `full_text` is shorter than 200 characters, `trafilatura` fetches and extracts the full article body from the URL.
2. **Deduplication** — TF-IDF vectorization (scikit-learn) computes pairwise cosine similarity; pairs above 0.85 are merged, keeping the article from the higher-credibility source (lower RSF press-freedom rank).

#### Step 4 — Streaming via `iter_articles()`
`NewsCrawlerAgent.iter_articles(query)` is an async generator that yields deduplicated `Article` objects one at a time. This allows the orchestrator to start bias analysis tasks concurrently with article fetching. A hard cap of `_MAX_ARTICLES = 12` limits total articles per query. Romanian-language detection adds `"ro"` to the GNews language list when the query contains Romanian text.

#### Data Model
```python
class Article(BaseModel):
    title: str
    full_text: str
    url: str
    source_id: str          # maps to source_registry.json
    source_name: str
    country: str            # ISO 3166-1 alpha-2; "EU" maps to "BE" (Brussels)
    published_at: datetime
    author: str | None
    language: str
    translated_text: str | None

class ArticleBundle(BaseModel):
    query: str
    articles: list[Article]
    sources_covered: list[str]
    countries_covered: list[str]
    crawl_timestamp: datetime
```

---

## Agent 2: Bias Analyst Agent

### Purpose
Given a set of articles on the same topic from different sources, this agent analyzes how each source's geopolitical context influences its coverage, then synthesizes a comparative report.

### How It Works

#### Step 1 — Source Profiling
For each article, `BiasAnalystAgent.analyze_article()` looks up the source in the registry to retrieve:
- Country of origin and geopolitical alliance bloc
- Ownership structure (state-funded, private, public trust)
- Known editorial lean
- RSF press-freedom rank

This profile is injected into the per-article LLM prompt as context.

#### Step 2 — Per-Article LLM Analysis
`article_analyzer.py` sends a structured prompt to Ollama (`format: "json"`) requesting a flat JSON object:

| Field | Type | Description |
|---|---|---|
| `overall_bias_direction` | string | e.g. "pro-Western", "neutral", "state-aligned" |
| `confidence` | 0–1 float | Model's confidence in the assessment |
| `framing_analysis` | string | Natural-language explanation |
| `sentiment_score` | −1 to +1 | Negative → positive emotional tone |
| `loaded_terms` | list[str] | Politically charged terms flagged |
| `omissions` | list[str] | Topics covered elsewhere but absent here |
| `attribution_balance` | string | Who is quoted and how balanced |

Up to 3 retries on JSON/validation errors; mock fallback on persistent failure so one bad LLM call never blocks the pipeline.

#### Step 3 — Concurrent Streaming
Analysis tasks run under `asyncio.Semaphore(_ANALYSIS_CONCURRENCY = 2)` to avoid overwhelming a single Ollama process. The orchestrator emits `article_analysis` SSE events as each task completes (via `asyncio.as_completed`), so the frontend can progressively badge article cards without waiting for all analyses to finish.

#### Step 4 — Cross-Source Comparison
`comparator.py` produces the final `BiasReport` in two stages:

1. **Deterministic computation** (`_computed_report`):
   - `_consensus_facts()` — token-based Jaccard similarity clusters sentences across all articles; facts reported by ≥3 sources are surfaced
   - `_disputed_framings()` — groups per-article analyses by `overall_bias_direction`, extracts top terms per group
   - `_geopolitical_patterns()` — groups by alliance bloc, summarises dominant directions and average sentiment
   - `_balanced_summary()` — constructs a template-based neutral summary

2. **LLM refinement** — if Ollama is available, the computed report is sent to the LLM for narrative polish. On any error the deterministic result is returned as-is.

#### Data Model
```python
class ArticleBiasAnalysis(BaseModel):
    article_url: str
    source_id: str
    overall_bias_direction: str
    confidence: float
    framing_analysis: str
    loaded_terms: list[str]
    omissions: list[str]
    sentiment_score: float
    attribution_balance: str
    political_compass: PoliticalCompassPoint | None

class BiasReport(BaseModel):
    topic: str
    consensus_facts: list[str]
    disputed_framings: list[dict]   # {framing, sources_using_it, geopolitical_pattern, confidence, sentiment_score}
    per_article: list[ArticleBiasAnalysis]
    geopolitical_patterns: list[str]
    balanced_summary: str
    methodology_note: str
```

---

## App Architecture

### Backend (FastAPI + Python 3.14)

```
backend/app/
├── main.py                      # FastAPI app, CORS, /api/search SSE endpoint
├── agents/
│   ├── orchestrator.py          # Chains Agent 1 → Agent 2, yields SSE events
│   ├── crawler_agent.py         # Agent 1: iter_articles() async generator
│   ├── bias_agent.py            # Agent 2: analyze_article() + final_report()
│   ├── query_expander.py        # LLM-based sub-query generation
│   ├── extractor.py             # trafilatura extraction + TF-IDF dedup
│   ├── article_analyzer.py      # Per-article LLM bias analysis
│   ├── comparator.py            # Cross-source comparison (deterministic + LLM)
│   ├── prompts.py               # All LLM prompt templates
│   ├── source_registry.py       # Loads source_registry.json
│   └── searchers/
│       ├── newsapi.py           # NewsAPI.org REST searcher
│       ├── gnews.py             # GNews REST searcher
│       └── _source_map.py       # Fallback outlet name → ISO country code map
├── models/
│   ├── article.py               # Article, ArticleBundle Pydantic models
│   └── bias_report.py           # ArticleBiasAnalysis, BiasReport Pydantic models
├── services/
│   └── llm_service.py           # Ollama httpx wrapper (json_mode opt-in)
└── source_registry.json         # ~36 curated sources with metadata
```

### SSE Event Stream

`POST /api/search` returns a `text/event-stream` response. Events arrive in this order:

| Event type | When | Payload |
|---|---|---|
| `article` | As each article is crawled | `Article` |
| `article_analysis` | As each LLM analysis finishes | `ArticleBiasAnalysis` |
| `bias_report` | After all analyses + comparator | `BiasReport` |
| `error` | On unhandled failure | `{ message: string }` |
| `[DONE]` | Stream sentinel | — |

Other endpoints:
```
GET  /api/sources   →  list of all tracked sources with metadata
GET  /health        →  {"status": "ok"}
```

### Agent Orchestration (`orchestrator.py`)

```python
async def process_query(query: str) -> AsyncGenerator[dict, None]:
    # Phase 1: Crawl — stream articles as found, kick off analysis tasks concurrently
    async for article in crawler.iter_articles(query):
        yield {"type": "article", "data": article.model_dump()}
        pending.add(asyncio.create_task(analyze_with_limit(article)))
        async for event in emit_finished_analyses():   # emit any already-done tasks
            yield event

    # Phase 2: Drain remaining analysis tasks as they complete
    for task in asyncio.as_completed(pending):
        analysis, source_profile = await task
        yield {"type": "article_analysis", "data": analysis.model_dump()}

    # Phase 3: Cross-source comparison
    report = await analyst.final_report(query=query, articles=articles, ...)
    yield {"type": "bias_report", "data": report.model_dump()}
```

### Frontend (Next.js 14 + React 18 + TypeScript)

```
frontend/
├── app/
│   └── page.tsx                 # Main page: status machine, event handler, layout
├── components/
│   ├── SearchBar.tsx            # Search input; shows "Crawling…" spinner when active
│   ├── ArticleCard.tsx          # Article display with bias badge overlay
│   ├── BiasReportPanel.tsx      # Bias report: consensus facts, disputed framings
│   └── RegionMap.tsx            # react-simple-maps world map, country-click filter
└── lib/
    ├── streamClient.ts          # SSE generator (AbortSignal cancel support)
    └── iso.ts                   # ISO 3166-1 alpha-2 → numeric map (incl. EU → BE)
```

**Frontend status machine:**

```
idle → streaming (articles arrive + analyses badge in progressively)
     → done (bias_report received / stream ends)
     → error (network or backend exception)

done/error → streaming on new query
```

**RegionMap** highlights countries by article count, dims non-selected countries when a filter is active, and toggles country filtering on click. "EU"-coded articles map to Belgium (Brussels) via the `iso.ts` fallback.

---

## LLM Integration

The app runs entirely on a **local LLM via Ollama** — no cloud API calls, no API keys for inference.

| Setting | Default | Env var |
|---|---|---|
| Ollama URL | `http://localhost:11434` | `OLLAMA_URL` |
| Model | `llama3.2` | `OLLAMA_MODEL` |
| Mock mode | `false` | `LLM_MOCK` |

`LLMService.complete(prompt, json_mode=False)` wraps `POST /api/generate`. `json_mode=True` adds `"format": "json"` to the payload — this is opt-in because Ollama's JSON mode only supports objects (not arrays), and the query expander needs array output.

**Failure handling at every layer:**
- `query_expander`: LLM timeout → keyword fallback
- `article_analyzer`: JSON parse/validation failure → 3 retries → mock result
- `comparator`: LLM error → deterministic computed report
- `bias_agent.final_report`: exception → error SSE event (stream still closes cleanly)

---

## Technology Stack

| Component | Choice | Notes |
|---|---|---|
| LLM inference | Ollama (`llama3.2`) | Local, no API key required |
| News APIs | NewsAPI.org + GNews | Both optional; mock fallback if keys absent |
| Article extraction | trafilatura | Better than newspaper3k for modern sites |
| Deduplication | scikit-learn TF-IDF cosine | Threshold 0.85; keeps higher-credibility source |
| Backend | FastAPI + Python 3.14 | Async-native; `StreamingResponse` for SSE |
| Frontend | Next.js 14 + React 18 | App Router, TypeScript, Tailwind CSS |
| Map | react-simple-maps + world-atlas | TopoJSON; ISO numeric IDs for country matching |

---

## Geopolitical Bias Framework

### Alliance Blocs
- **NATO/Western**: US, UK, France, Germany, Canada, Australia, Israel
- **BRICS+**: China, Russia, India, Brazil, South Africa, Iran
- **Non-Aligned / Regional**: Turkey, Qatar, Singapore, ASEAN nations

### Ownership Categories
- **State-funded**: BBC (UK), RT (Russia), Xinhua (China), Al Jazeera (Qatar), NHK (Japan)
- **Private / Corporate**: CNN (Warner), Fox News (Fox Corp), Times of India (Bennett Coleman)
- **Public Trust**: NPR (US), ABC (Australia)

### Bias Signals the Agent Looks For
1. **Whose perspective is centred?** — Domestic government vs foreign actors
2. **What language is used for conflict?** — "Invasion" vs "special operation"
3. **What context is provided or omitted?** — Historical framing that favours one narrative
4. **Which experts/officials are quoted?** — Balance of voices
5. **What is the emotional register?** — Factual vs inflammatory

---

## Example Walkthrough

**User query:** *"South China Sea tensions 2026"*

**Agent 1 (Crawler) finds:**
- Reuters (GB): "Philippines files new maritime protest amid South China Sea standoff"
- Xinhua (CN): "China reaffirms sovereignty, calls for dialogue in South China Sea"
- CNN (US): "US Navy conducts freedom of navigation operation near disputed islands"
- The Straits Times (SG): "ASEAN urges restraint as South China Sea tensions flare"
- Global Times (CN): "US provocations destabilize South China Sea peace"

**Agent 2 (Bias Analyst) produces:**

| Source | Country | Framing | Key Bias Signal |
|---|---|---|---|
| Reuters | GB | Neutral descriptive | Most balanced; uses "disputed" consistently |
| Xinhua | CN | China as peaceful, others as provocateurs | Omits Philippine legal claims; frames as "sovereignty" |
| CNN | US | US as defender of international order | Centres US military action; limited Chinese perspective |
| Straits Times | SG | Regional stability focus | ASEAN-centric; avoids taking sides |
| Global Times | CN | US as aggressor | Loaded language ("provocations", "destabilize"); no US quotes |

**Geopolitical Pattern:** *"Coverage splits along alliance lines: US-aligned sources frame freedom-of-navigation as lawful; China-aligned sources frame it as provocation. Regional sources (ASEAN) focus on de-escalation."*

**Balanced Summary:** *"Multiple nations are involved in overlapping territorial claims in the South China Sea. The Philippines has filed a diplomatic protest, China has reasserted its sovereignty claims while calling for bilateral talks, and the US conducted a naval operation citing international maritime law. ASEAN has called for restraint from all parties."*

---

## Why the Agents Are "Embedded" (Not Bolted On)

1. **No Agent 1 → No content.** The app has no pre-loaded news database. Every piece of content comes from Agent 1's real-time crawling on each query.
2. **No Agent 2 → No differentiation.** Without bias analysis this is just another news aggregator. Agent 2's output is what makes every article card, every comparison view, and every summary unique.
3. **The orchestrator IS the backend.** `POST /api/search` is essentially: receive query → run Agent 1 → run Agent 2 → stream results. The agents are not called from a sidebar; they are the main pipeline.

This means the agents demonstrate:
- **Architectural embeddedness** — they are the data pipeline, not a feature flag
- **Autonomous behaviour** — Agent 1 decides what to search; Agent 2 decides what counts as bias
- **Tool use** — Agent 1 uses search APIs as tools; Agent 2 uses the source registry as a knowledge base
- **Agent chaining** — output of Agent 1 feeds directly into Agent 2, with streaming overlap
