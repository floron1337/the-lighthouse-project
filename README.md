# The Lighthouse

> Read the news. See the framing.

The Lighthouse is a news application powered by two embedded AI agents that form the core data pipeline:

1. **News Crawler Agent** — given a user query, finds articles from diverse international sources (NewsAPI, GNews, RSS feeds, regional outlets).
2. **Bias Analyst Agent** — analyzes those articles for geopolitical bias (framing, loaded language, omissions, attribution patterns) and produces a comparative report.

Every user query triggers Agent 1 → Agent 2 → streamed UI updates. See [`DESIGN.md`](DESIGN.md) for the full architecture.

---

## Setup

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.11+ | 3.14 works fine |
| `uv` | any | preferred; falls back to `pip` |
| Node.js | 18+ | |
| `pnpm` | any | preferred; falls back to `npm` |

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — API keys are optional in mock mode (the default)
```

### 2. Backend

```bash
cd backend

# With uv (preferred):
uv sync
uvicorn app.main:app --reload

# Without uv (pip fallback):
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API starts at **http://localhost:8000**.

### 3. Frontend

```bash
cd frontend

# With pnpm (preferred):
pnpm install
pnpm dev

# Without pnpm (npm fallback):
npm install
npm run dev
```

The UI starts at **http://localhost:3000**.

---

## Environment Variables

| Variable | Used in | Required for mock mode? |
|---|---|---|
| `ANTHROPIC_API_KEY` | `backend/app/services/llm_service.py` | No |
| `NEWSAPI_KEY` | `backend/app/agents/searchers/newsapi.py` | No |
| `GNEWS_KEY` | `backend/app/agents/searchers/gnews.py` | No |
| `NEXT_PUBLIC_BACKEND_URL` | `frontend/lib/streamClient.ts` | No (defaults to `http://localhost:8000`) |

All keys default to mock mode when not set — the app is fully functional with synthetic data out of the box.

---

## Running Tests

```bash
cd backend
# With uv:
uv run pytest tests/ -v

# With pip venv activated:
pytest tests/ -v
```

Expected output: 4 passing tests in `tests/test_orchestrator_mock.py`.

---

## Pick Up a Ticket

> Each section names the exact file to open and what the teammate needs to implement.

### THE-6 — Source Registry (expand to ~100 sources)
**File:** [`backend/app/source_registry.json`](backend/app/source_registry.json)

The registry has 20 seed sources. Expand it to ~100 by adding underrepresented regions: Sub-Saharan Africa (e.g. Mail & Guardian, Daily Nation), Latin America (e.g. Folha de S.Paulo, Infobae), Central Asia, and more ASEAN outlets. Each entry needs: `id`, `name`, `country`, `region`, `ownership`, `known_lean`, `alliance_bloc`, `rss_url`, `language`, `credibility_score`. Add RSS URL validation logic in [`backend/app/agents/source_registry.py`](backend/app/agents/source_registry.py).

### THE-7 — Query Expander
**File:** [`backend/app/agents/query_expander.py`](backend/app/agents/query_expander.py)

Replace the mock in `expand()` with a real LLM call. Use `llm_service.complete()` with the prompt template in [`backend/app/agents/prompts.py`](backend/app/agents/prompts.py) (`QUERY_EXPANSION_PROMPT`). Parse the returned JSON array and return it as `list[str]`. Add error handling for malformed LLM output (retry once, then fall back to the mock).

### THE-8 — News API Searchers
**Files:** [`backend/app/agents/searchers/newsapi.py`](backend/app/agents/searchers/newsapi.py), [`backend/app/agents/searchers/gnews.py`](backend/app/agents/searchers/gnews.py)

Replace the mock returns with real `httpx.AsyncClient` calls. For NewsAPI, hit `/v2/everything` with `q`, `from` (7 days ago), `language=en`, and `apiKey` params. For GNews, hit `/v4/search`. Map JSON responses to `Article` models — resolve `source_id` from the registry by fuzzy-matching `source.name`. Read keys from `os.environ["NEWSAPI_KEY"]` and `os.environ["GNEWS_KEY"]`. Handle 429 rate-limiting gracefully (return empty list, log warning).

### THE-9 — Article Extractor & Deduplicator
**File:** [`backend/app/agents/extractor.py`](backend/app/agents/extractor.py)

Implement `extract_and_dedupe()`. First uncomment `trafilatura` and/or `newspaper3k` in [`backend/pyproject.toml`](backend/pyproject.toml). For each article whose `full_text` is a stub or snippet, fetch the URL and extract clean body text with trafilatura. Then deduplicate: compute TF-IDF vectors (or OpenAI `text-embedding-3-small`) for all articles, drop pairs with cosine similarity > 0.85 (keep the higher-credibility source).

### THE-10 — Source Profiler
**File:** [`backend/app/agents/source_profiler.py`](backend/app/agents/source_profiler.py)

Enrich `get_source_profile()` with RSF press-freedom index data (rsf.org/en/index) keyed by ISO country code — store as a local JSON file to avoid live API calls. Optionally query the LLM for a one-sentence editorial-history summary of the outlet. The richer profile is passed to `article_analyzer.py` as the `source_profile` dict.

### THE-11 — Article Analyzer
**File:** [`backend/app/agents/article_analyzer.py`](backend/app/agents/article_analyzer.py)

Replace the mock in `analyze()` with a structured LLM call. Inject article text and source profile into `prompts.BIAS_ANALYSIS_PROMPT`, call `llm_service.complete()`, parse the JSON response into an `ArticleBiasAnalysis`. Add one retry on `json.JSONDecodeError`. Validate that `sentiment_score` is in `[-1, 1]` and `confidence` is in `[0, 1]`.

### THE-14 — Comparator
**File:** [`backend/app/agents/comparator.py`](backend/app/agents/comparator.py)

Replace the mock in `compare()` with real comparison logic. Group analyses by `alliance_bloc`, find facts mentioned in 3+ articles (string overlap or embedding similarity), cluster disputed framings, and call the LLM with `prompts.BIAS_COMPARISON_PROMPT` to generate `balanced_summary`. Return a fully populated `BiasReport`. All existing tests in `tests/test_orchestrator_mock.py` must still pass.
