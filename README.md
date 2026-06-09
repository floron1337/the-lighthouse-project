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
| Ollama | any | optional; only needed when `LLM_MOCK=false` |

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — mock mode is enabled by default
```

To run real local LLM analysis instead of mock responses, install Ollama,
pull the configured model, and set `LLM_MOCK=false`:

```bash
ollama pull llama3.2
ollama serve
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

| Variable | Used in | Required? |
|---|---|---|
| `LLM_MOCK` | `backend/app/services/llm_service.py` | No — set `true` to skip Ollama calls (default: `false`) |
| `OLLAMA_URL` | `backend/app/services/llm_service.py` | No (defaults to `http://localhost:11434`) |
| `OLLAMA_MODEL` | `backend/app/services/llm_service.py` | No (defaults to `llama3.2`) |
| `NEWSAPI_KEY` | `backend/app/agents/searchers/newsapi.py` | No — omit to use mock article fallback |
| `GNEWS_KEY` | `backend/app/agents/searchers/gnews.py` | No — omit to use mock article fallback |
| `NEXT_PUBLIC_BACKEND_URL` | `frontend/lib/streamClient.ts` | No (defaults to `http://localhost:8000`) |

With `LLM_MOCK=true`, the app is functional with synthetic LLM output and
does not require Ollama. With `LLM_MOCK=false`, `LLMService` sends prompts to
Ollama's `/api/generate` endpoint using `OLLAMA_MODEL`.

---

## Docker

```bash
# Run the full stack with Docker Compose (mock LLM, no Ollama required)
docker compose up --build

# With real Ollama running on the host
LLM_MOCK=false docker compose up --build
```

Production images are automatically built and published to the GitHub Container Registry on every push to `main` by the [CD workflow](.github/workflows/docker-publish.yml):

```bash
docker pull ghcr.io/floron1337/the-lighthouse-project/backend:latest
docker pull ghcr.io/floron1337/the-lighthouse-project/frontend:latest
```

---

## Running Tests

```bash
cd backend
# With uv:
uv run pytest tests/ -v

# With pip venv activated:
pytest tests/ -v
```

Expected output: all tests passing across 9 test files in `tests/`.

---

## AI-Assisted Development Report

This section documents **how AI tools were used during the development process** — design, implementation, debugging, and documentation. It is distinct from the [AI Tools Usage Report](#ai-tools-usage-report) below, which covers AI running inside the application at runtime.

---

### Tools Used

| Tool | Role in development |
|---|---|
| **Claude Code** (Anthropic) | Primary development assistant — architecture design, full-stack implementation, debugging, tests, documentation |
| **Linear** | AI-assisted backlog generation and user story writing (Linear's built-in AI feature) |
| **GitHub Copilot** | In-editor autocomplete for boilerplate and type annotations |

---

### Phase 1 — Architecture & Design

The initial architecture (two-agent pipeline, SSE streaming, Pydantic data models) was designed in conversation with **Claude Code**. The agent asked clarifying questions about LLM hosting requirements ("should we build a separate LLM microservice?") and recommended using the existing Ollama daemon as the shared inference layer instead of a new service — avoiding unnecessary complexity.

**Claude Code** also generated the full `DESIGN.md` and `docs/ARCHITECTURE_UML.md`, including the 5 Mermaid diagrams (component topology, class diagram, sequence diagram, frontend component tree, state machine).

**Linear's AI** was used to draft the initial backlog from a one-paragraph project description, producing 14 user stories with acceptance criteria. These were then reviewed and refined manually.

---

### Phase 2 — Implementation

Virtually the entire backend was implemented by **Claude Code** across iterative sessions:

| Module | What AI wrote |
|---|---|
| `llm_service.py` | Full rewrite from Anthropic SDK → Ollama httpx client; `json_mode` opt-in design |
| `query_expander.py` | LLM-based sub-query generation with array-output fallback |
| `searchers/newsapi.py` | Full NewsAPI integration with query sanitization and rate-limit handling |
| `searchers/gnews.py` | Full GNews integration with 400/429 handling |
| `searchers/_source_map.py` | ~120-entry outlet name → ISO country code fallback map; EU outlet ordering fix |
| `extractor.py` | trafilatura fetch + TF-IDF cosine deduplication (scikit-learn) |
| `article_analyzer.py` | LLM bias analysis with 3-retry logic, key alias normalization, mock fallback |
| `comparator.py` | Deterministic cross-source report (token clustering, Jaccard similarity) + LLM refinement |
| `orchestrator.py` | Full streaming pipeline: `iter_articles()` + `asyncio.as_completed` + semaphore concurrency |
| `bias_agent.py` | `analyze_article()` and `final_report()` interface methods |

Frontend features implemented by **Claude Code**:
- Country-click filter on the world map (ISO alpha-2 ↔ numeric TopoJSON ID conversion)
- `crawl_done` / `error` SSE event types and phase-aware status (`streaming → analyzing → done`)
- Stop/cancel button with `AbortController` wired through `streamSearch(signal)`
- EU source → Belgium map fallback (`EU: "056"` in `iso.ts`)

**GitHub Copilot** was used for repetitive boilerplate — Pydantic model field declarations, TypeScript interface property lists, and test fixture setup — reducing keystrokes without changing design decisions.

---

### Phase 3 — Debugging

All significant bugs were diagnosed and fixed with **Claude Code**:

| Bug | Root cause found by AI | Fix |
|---|---|---|
| `KeyError: '\n  "overall_bias_direction"'` | Python `.format()` treating `{}` in JSON example as placeholders | Escaped prompt braces to `{{` / `}}` |
| GNews 400 on queries with apostrophes | API rejects unquoted special chars | `re.sub(r"[\"'\`]", "", query)` sanitization |
| 2-minute silent hang on query expansion | `format:"json"` + array output = Ollama loops forever | Made `json_mode` opt-in; added `except Exception` fallback |
| LLM returning `{"analysis": {"Framing": ...}}` nested JSON | llama3.2 wraps output in an `analysis` key and capitalises field names | `_parse_response` flattening + key alias normalization |
| Map showing few countries | Sources not in 20-entry registry defaulted to `"XX"` | Extended `_source_map.py` to ~120 entries |
| Stop button not working during initial crawl | Cancel button was inside `{hasResults && ...}`, invisible before first article | Moved Stop to `SearchBar` component, always visible |

---

### Phase 4 — Testing

The test suite (9 backend files, 1 frontend file) was written by **Claude Code**:

- `test_orchestrator_mock.py` — end-to-end pipeline tests with `LLM_MOCK=true`; verifies event ordering, required fields, and analysis/article count parity
- `test_article_analyzer.py` — uses `FakeLLMService` (controlled response injection) and `FailingLLMService` (simulates Ollama unavailability) to test retry logic and fallback behaviour
- `test_comparator.py`, `test_bias_agent.py` — deterministic report generation tests
- `test_crawler_agent.py`, `test_query_expander.py` — unit tests for Agent 1 components
- `test_source_resolution.py`, `test_source_profiler.py` — country resolution and source profile tests

The CI pipelines (`.github/workflows/backend-tests.yml`, `frontend-tests.yml`) were also generated by **Claude Code**, including matrix testing on Python 3.11 and 3.12.

---

### Phase 5 — Documentation

All documentation was written by **Claude Code** based on the implemented code:

- `README.md` — setup guide, env vars table, test instructions, this report
- `DESIGN.md` — full architecture document updated to match the real implementation
- `docs/ARCHITECTURE_UML.md` — 5 UML diagrams generated as PNGs via `mmdc`

---

### Assessment

| Aspect | Result |
|---|---|
| Code written by AI (backend) | ~95% — AI wrote all agent implementations, models, and tests |
| Code written by AI (frontend) | ~60% — AI wrote new features; base UI scaffolding was pre-existing |
| Bugs introduced by AI and fixed by AI | All major bugs were introduced and fixed in the same AI sessions |
| Design decisions made by AI | Ollama over cloud API, opt-in `json_mode`, semaphore concurrency, TF-IDF over embeddings |
| Design decisions made by humans | Project concept, geopolitical framing, source registry curation, UI aesthetics |

The primary limitation observed: **local LLMs (llama3.2 3B) hallucinate heavily on structured JSON output**, requiring extensive retry logic and prompt engineering that a cloud model (GPT-4o, Claude Sonnet) would not have needed. This was a deliberate trade-off chosen for the project to avoid cloud API costs and keep the system self-hosted.

---

## AI Tools Usage Report

This section documents every point at which artificial intelligence is used inside the application — what model runs, what it receives, what it produces, and what safeguards are in place.

---

### Local LLM Infrastructure

The application runs **no cloud AI APIs in production**. All language-model inference is served by a local [Ollama](https://ollama.com) daemon (`localhost:11434`). The default model is **llama3.2** (2 GB, Meta Llama 3.2 3B), configured via `OLLAMA_MODEL`. Any Ollama-compatible model can be substituted.

The shared abstraction is [`backend/app/services/llm_service.py`](backend/app/services/llm_service.py):

```
LLMService.complete(prompt, json_mode=False)
    │
    ├─ use_mock=True  →  returns a canned string (dev / CI)
    └─ use_mock=False →  POST http://localhost:11434/api/generate
                            model:   OLLAMA_MODEL
                            stream:  false
                            format:  "json"  (when json_mode=True)
                            options: temperature=0.2
```

Setting `json_mode=True` passes Ollama's grammar-constrained JSON mode, which forces the tokenizer to only emit tokens that keep the output as valid JSON. This is used for the two structured-output calls (bias analysis and comparison) but **not** for query expansion, which expects a JSON array that the constraint would prevent.

---

### Agent 1 — News Crawler Agent

**File:** [`backend/app/agents/crawler_agent.py`](backend/app/agents/crawler_agent.py)

The crawler has one AI-powered step:

#### Step 1.1 — Query Expansion (THE-7)

**File:** [`backend/app/agents/query_expander.py`](backend/app/agents/query_expander.py)

| | |
|---|---|
| **When** | Once per user request, before any API calls |
| **Input** | Raw user query string (e.g. `"South China Sea tensions"`) |
| **Prompt** | `QUERY_EXPANSION_PROMPT` in [`backend/app/agents/prompts.py`](backend/app/agents/prompts.py) |
| **Output** | JSON array of 3 sub-query strings covering: exact topic, geopolitical angle, temporal variant |
| **Fallback** | `[query, "{query} 2026", "{query} international"]` on any LLM or parse failure |

The expanded sub-queries are each sent to both NewsAPI and GNews in parallel, broadening geographic and framing coverage before any bias analysis begins.

---

### Agent 2 — Bias Analyst Agent

**File:** [`backend/app/agents/bias_agent.py`](backend/app/agents/bias_agent.py)

The analyst has two AI-powered steps:

#### Step 2.1 — Per-Article Bias Analysis (THE-11)

**File:** [`backend/app/agents/article_analyzer.py`](backend/app/agents/article_analyzer.py)

| | |
|---|---|
| **When** | Once per article, all articles analyzed in parallel (`asyncio.gather`) |
| **Input** | Article title + first 2 000 chars of body text; source metadata (outlet, country, ownership, editorial lean, alliance bloc) |
| **Prompt** | `BIAS_ANALYSIS_PROMPT` in [`prompts.py`](backend/app/agents/prompts.py) |
| **Output** | `ArticleBiasAnalysis` JSON object with 7 fields (see model below) |
| **JSON mode** | Yes — `json_mode=True` forces valid JSON object output |
| **Retries** | Up to 3 attempts on parse/validation error; mock fallback on final failure |
| **Fallback** | Mock analysis derived from source registry metadata (no crash) |

Output fields (`ArticleBiasAnalysis`):

| Field | Type | Description |
|---|---|---|
| `overall_bias_direction` | `str` | One of: `pro-Western`, `pro-BRICS`, `pro-government`, `neutral`, `mixed` |
| `confidence` | `float 0–1` | Model's self-reported confidence in the classification |
| `framing_analysis` | `str` | How the headline and lede frame the story |
| `sentiment_score` | `float −1–+1` | Emotional valence of the article text |
| `loaded_terms` | `list[str]` | Politically charged or emotionally loaded words found in the text |
| `omissions` | `list[str]` | Context typically covered by other sources but absent here |
| `attribution_balance` | `str` | Who is quoted and whether representation is balanced |

#### Step 2.2 — Cross-Source Comparison (THE-14)

**File:** [`backend/app/agents/comparator.py`](backend/app/agents/comparator.py)

| | |
|---|---|
| **When** | Once per request, after all per-article analyses complete |
| **Input** | All `ArticleBiasAnalysis` results, summarised as one line per article (source, bias direction, framing snippet, loaded terms) |
| **Prompt** | `BIAS_COMPARISON_PROMPT` in [`prompts.py`](backend/app/agents/prompts.py) |
| **Output** | 4 fields of `BiasReport`: `consensus_facts`, `disputed_framings`, `geopolitical_patterns`, `balanced_summary` |
| **JSON mode** | Yes — `json_mode=True` |
| **Fallback** | Mock report with alliance-bloc groupings derived from per-article results (no crash) |

---

### Prompt Design

All prompts are in [`backend/app/agents/prompts.py`](backend/app/agents/prompts.py). Design choices:

- **Temperature 0.2** across all calls — low enough for consistent structured output, high enough to avoid degenerately repetitive phrasing.
- **Explicit JSON schema in the prompt** — the bias analysis prompt includes the exact key names and types so the model does not need to infer schema from context.
- **No chain-of-thought** — the prompts ask directly for the output JSON. For a 3B model, COT would consume context without improving classification accuracy on this task.
- **2 000-character article truncation** — llama3.2's context window is 128 k tokens, but longer inputs slow inference significantly; 2 000 chars (≈ 400 tokens) captures the lede, key claims, and framing, which is where bias most clearly manifests.

---

### Failure Modes & Safeguards

| Failure | Handling |
|---|---|
| Ollama not running / unreachable | `httpx.ConnectError` caught in `query_expander`; orchestrator catches all crawler exceptions and yields `{"type": "error", ...}` to the frontend |
| LLM returns empty string | Detected before JSON parse; immediately uses mock fallback (no wasted retries) |
| LLM returns nested/malformed JSON | `_parse_response` in `article_analyzer.py` flattens `analysis` wrappers, normalises capitalised key variants, and provides string/list defaults before Pydantic validation |
| LLM returns invalid JSON despite `json_mode` | Up to 3 retries; mock fallback on final failure |
| News API rate-limit (429) or bad query (400) | Searchers return `[]`; crawler falls back to 5 mock articles if fewer than 3 unique source IDs are found |
| Article URL fetch fails during text extraction | Per-URL `try/except` in `extractor.py`; article keeps its truncated text |

---

### Mock Mode

Setting `LLM_MOCK=true` (or not setting it in `.env`) bypasses all Ollama calls. Every agent step returns deterministic synthetic data. This is the default for:

- Local development without Ollama installed
- CI (GitHub Actions `frontend-tests.yml`)
- The 4 backend unit tests in `tests/test_orchestrator_mock.py`

