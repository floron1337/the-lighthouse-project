# News App — AI Agent Architecture Design

## Overview

This document describes the architecture for a news application with **two embedded AI agents**:

1. **News Crawler Agent** — crawls the internet for news on a user-prompted topic, discovers relevant articles from multiple news channels across different countries/regions.
2. **Bias Analyst Agent** — takes the collected articles and performs comparative bias analysis based on each news channel's country of origin, geopolitical alignment, ownership, and editorial history.

The agents are not bolt-on features — they are **core to the app's data flow**. Every user query triggers both agents in sequence as part of the app's pipeline.

---

## High-Level Data Flow

```
┌──────────────┐
│   User Prompt │  e.g. "Russia-Ukraine ceasefire talks"
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         AGENT 1: News Crawler            │
│                                          │
│  1. Interprets user query                │
│  2. Expands into search sub-queries      │
│  3. Searches news APIs + web scraping    │
│  4. Filters & deduplicates results       │
│  5. Extracts article text + metadata     │
│     (source, country, date, author)      │
│                                          │
│  Output: List[ArticleBundle]             │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│       AGENT 2: Bias Analyst              │
│                                          │
│  1. Receives articles on the same topic  │
│  2. Classifies each source's profile     │
│     (country, state/private ownership,   │
│      known editorial lean, geopolitical  │
│      alliance bloc)                      │
│  3. Performs per-article analysis:        │
│     - Framing & headline tone            │
│     - Omissions vs other sources         │
│     - Language sentiment & loaded terms   │
│     - Source attribution patterns         │
│  4. Produces comparative bias report     │
│                                          │
│  Output: BiasReport                      │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│              App Frontend                │
│                                          │
│  - Article cards grouped by source       │
│  - Side-by-side comparison view          │
│  - Bias indicators per article/source    │
│  - Explanation panel (why bias flagged)  │
│  - "Balanced summary" generated view     │
└──────────────────────────────────────────┘
```

---

## Agent 1: News Crawler Agent

### Purpose
Given a user's natural-language prompt (e.g. *"What's happening with the EU AI Act?"*), this agent autonomously finds relevant news articles from **diverse international sources**.

### How It Works

#### Step 1 — Query Understanding & Expansion
The agent uses an LLM to:
- Parse the user's intent and extract key entities/topics
- Generate multiple search sub-queries to maximize coverage
  - e.g. for "EU AI Act": `["EU AI Act regulation 2026", "European AI law impact tech companies", "EU artificial intelligence act vote"]`
- Identify relevant geographies to target (to ensure diverse sourcing)

#### Step 2 — Multi-Source Search
The agent queries multiple data sources in parallel:

| Source Type | Examples | Method |
|---|---|---|
| News APIs | NewsAPI.org, GNews, MediaStack, Google News RSS | REST API calls |
| News Aggregators | Google News, Bing News | Headless Selenium scraping |
| Direct RSS feeds | BBC, Al Jazeera, RT, Xinhua, Reuters, NHK, etc. | RSS parsing |
| Regional sources | Country-specific outlets curated in a source registry | Targeted scraping |

**Source Registry** — A curated database of ~100+ news channels with metadata:
```json
{
  "id": "bbc_news",
  "name": "BBC News",
  "country": "GB",
  "region": "Western Europe",
  "ownership": "state_funded",
  "known_lean": "centre",
  "alliance_bloc": "NATO/Five Eyes",
  "rss_url": "http://feeds.bbci.co.uk/news/rss.xml",
  "language": "en",
  "credibility_score": 0.85
}
```

#### Step 3 — Article Extraction & Deduplication
- Extract full article text using `newspaper3k` or `trafilatura`
- Deduplicate based on semantic similarity (embedding cosine distance)
- Normalize metadata: publication date, author, source attribution

#### Step 4 — Output: ArticleBundle
```python
@dataclass
class Article:
    title: str
    full_text: str
    url: str
    source_id: str          # maps to source registry
    source_name: str
    country: str
    published_at: datetime
    author: Optional[str]
    language: str            # original language
    translated_text: Optional[str]  # English translation if needed

@dataclass
class ArticleBundle:
    query: str
    articles: List[Article]
    sources_covered: List[str]
    countries_covered: List[str]
    crawl_timestamp: datetime
```

### Integration in the App
The News Crawler Agent is triggered **every time a user submits a query**. It is the app's primary data ingestion layer — there is no pre-populated news database. The app is "pull-based": user asks → agent crawls → results appear.

The agent runs as an **async pipeline** so the UI can stream partial results (show articles as they're found, rather than waiting for all sources).

---

## Agent 2: Bias Analyst Agent

### Purpose
Given a set of articles on the same topic from different sources, this agent analyzes and explains how each source's **geopolitical context** influences its coverage.

### How It Works

#### Step 1 — Source Profiling
For each article's source, the agent loads or builds a profile:
- **Country of origin** and its geopolitical alliances (NATO, BRICS, Non-Aligned, etc.)
- **Ownership structure** (state-funded, private, oligarch-owned, public trust)
- **Historical editorial patterns** (from the source registry + LLM knowledge)
- **Regulatory environment** (press freedom index of the country)

#### Step 2 — Per-Article Analysis
The agent uses an LLM with structured prompting to analyze each article across these dimensions:

| Dimension | What It Detects | Example |
|---|---|---|
| **Framing** | How the headline/lede frames the story | "Peace talks progress" vs "Ukraine forced to negotiate" |
| **Tone & Sentiment** | Emotional valence of language | Neutral reporting vs alarmist language |
| **Loaded Language** | Politically charged terms | "regime" vs "government", "freedom fighters" vs "militants" |
| **Omissions** | What other sources cover but this one doesn't | Source A covers civilian casualties, Source B doesn't mention them |
| **Attribution** | Who is quoted and how | Only quoting one side's officials |
| **Causal Framing** | Who/what is blamed or credited | "Country X provoked..." vs "Country Y responded to..." |

#### Step 3 — Cross-Source Comparison
The agent compares articles pairwise and collectively:
- Identifies **consensus facts** (reported by all/most sources)
- Identifies **disputed framing** (same event, different interpretations)
- Maps framing patterns to **geopolitical alignment** (e.g. all NATO-aligned sources use framing A, BRICS-aligned sources use framing B)
- Highlights **unique information** only available in specific sources

#### Step 4 — Output: BiasReport
```python
@dataclass
class ArticleBiasAnalysis:
    article_url: str
    source_id: str
    overall_bias_direction: str      # e.g. "pro-Western", "pro-government", "neutral"
    confidence: float                # 0-1
    framing_analysis: str            # natural language explanation
    loaded_terms: List[str]          # flagged terms with explanations
    omissions: List[str]             # topics covered by others but missing here
    sentiment_score: float           # -1 (very negative) to +1 (very positive)
    attribution_balance: str         # who is quoted / how balanced

@dataclass
class BiasReport:
    topic: str
    consensus_facts: List[str]       # agreed upon by most sources
    disputed_framings: List[dict]    # {framing, sources_using_it, geopolitical_pattern}
    per_article: List[ArticleBiasAnalysis]
    geopolitical_patterns: List[str] # high-level observations
    balanced_summary: str            # LLM-generated neutral summary
    methodology_note: str            # transparency about how analysis was done
```

### Integration in the App
The Bias Analyst Agent runs **automatically after Agent 1 returns results**. It is not a separate feature the user opts into — it is how the app presents news. Every article card in the UI shows its bias indicators. The comparison view is the app's primary reading interface.

---

## App Architecture (How Agents Are Embedded)

### Backend (FastAPI)

```
app/
├── main.py                     # FastAPI app, CORS, routes
├── agents/
│   ├── crawler_agent.py        # Agent 1 implementation
│   │   ├── query_expander.py   # LLM-based query expansion
│   │   ├── source_registry.py  # Curated news source database
│   │   ├── searchers/          # NewsAPI, RSS, Selenium scrapers
│   │   └── extractor.py        # Article text extraction
│   ├── bias_agent.py           # Agent 2 implementation
│   │   ├── source_profiler.py  # Geopolitical source profiling
│   │   ├── article_analyzer.py # Per-article bias analysis
│   │   ├── comparator.py       # Cross-source comparison
│   │   └── prompts.py          # LLM prompt templates
│   └── orchestrator.py         # Chains Agent 1 → Agent 2
├── models/
│   ├── article.py              # Article, ArticleBundle dataclasses
│   └── bias_report.py          # BiasReport dataclasses
├── services/
│   ├── llm_service.py          # OpenAI/Anthropic API wrapper
│   └── cache_service.py        # Cache recent queries
└── source_registry.json        # Curated source metadata
```

### Key API Endpoints

```
POST /api/search
  Body: { "query": "EU AI Act latest developments" }
  Response: Streamed — first articles, then bias report
  
GET  /api/report/{report_id}
  Response: Full BiasReport for a completed query

GET  /api/sources
  Response: List of all tracked news sources with metadata
```

### Agent Orchestration Flow (orchestrator.py)

```python
async def process_query(query: str) -> AsyncGenerator:
    # Phase 1: Crawl
    crawler = NewsCrawlerAgent(source_registry, llm_service)
    article_bundle = await crawler.search(query)
    
    # Stream articles to frontend as they arrive
    for article in article_bundle.articles:
        yield {"type": "article", "data": article}
    
    # Phase 2: Analyze bias
    analyst = BiasAnalystAgent(source_registry, llm_service)
    bias_report = await analyst.analyze(article_bundle)
    
    # Stream bias report
    yield {"type": "bias_report", "data": bias_report}
```

### Frontend Integration

The UI is designed around the agents' outputs:

1. **Search Bar** — User types a topic → triggers `POST /api/search`
2. **Article Stream** — Cards appear as Agent 1 finds them (SSE/WebSocket streaming)
   - Each card shows: headline, source, country flag, publication date
3. **Bias Overlay** — Once Agent 2 completes, each card gets:
   - A bias indicator badge (color-coded)
   - "Why?" expandable panel explaining the bias assessment
4. **Comparison View** — Side-by-side view of how 2-3 sources covered the same story
   - Highlighted differences in framing
   - Omission callouts
5. **Balanced Summary** — A generated neutral summary at the top, with methodology disclosure

---

## Technology Choices

| Component | Recommended | Why |
|---|---|---|
| LLM | OpenAI GPT-4o or Anthropic Claude | Best at nuanced bias analysis; structured output support |
| News APIs | NewsAPI.org (free tier: 100 req/day) + GNews | Broad coverage, easy integration |
| Web scraping | Selenium (headless) + trafilatura | Handles JS-rendered pages; good article extraction |
| Embeddings | OpenAI `text-embedding-3-small` | For deduplication via cosine similarity |
| Translation | DeepL API or Google Translate | For non-English sources |
| Backend | FastAPI + Python | Async-native, good LLM library ecosystem |
| Frontend | React or Next.js | Component-based UI for article cards + comparison views |
| Caching | SQLite or Redis | Avoid re-crawling identical queries within a time window |

---

## Geopolitical Bias Framework

The Bias Analyst Agent uses this framework to contextualize sources:

### Alliance Blocs (simplified)
- **NATO/Western**: US, UK, France, Germany, Canada, Australia, etc.
- **BRICS+**: China, Russia, India, Brazil, South Africa, Iran, etc.
- **Non-Aligned / Regional**: Turkey, Israel, Gulf States, ASEAN nations, etc.

### Ownership Categories
- **State-funded**: BBC (UK), RT (Russia), Xinhua (China), Al Jazeera (Qatar), NHK (Japan)
- **Private / Corporate**: CNN (Warner), Fox News (Fox Corp), Times of India (Bennett Coleman)
- **Public Trust**: NPR (US), ABC (Australia), ARD/ZDF (Germany)

### Bias Signals the Agent Looks For
1. **Whose perspective is centered?** — Domestic government vs foreign actors
2. **What language is used for conflict?** — "Invasion" vs "special operation" vs "intervention"
3. **What context is provided or omitted?** — Historical context that supports one narrative
4. **Which experts/officials are quoted?** — Balance of voices
5. **What is the emotional register?** — Factual vs inflammatory

---

## Example Walkthrough

**User query:** *"South China Sea tensions 2026"*

**Agent 1 (Crawler) finds:**
- Reuters (UK): "Philippines files new maritime protest amid South China Sea standoff"
- Xinhua (China): "China reaffirms sovereignty, calls for dialogue in South China Sea"
- CNN (US): "US Navy conducts freedom of navigation operation near disputed islands"  
- The Straits Times (Singapore): "ASEAN urges restraint as South China Sea tensions flare"
- Global Times (China): "US provocations destabilize South China Sea peace"

**Agent 2 (Bias Analyst) produces:**

| Source | Country | Framing | Key Bias Signal |
|---|---|---|---|
| Reuters | UK/Intl | Neutral descriptive | Most balanced; uses "disputed" consistently |
| Xinhua | China | China as peaceful, others as provocateurs | Omits Philippine legal claims; frames as "sovereignty" |
| CNN | US | US as defender of international order | Centers US military action; limited Chinese perspective |
| Straits Times | Singapore | Regional stability focus | ASEAN-centric; avoids taking sides |
| Global Times | China | US as aggressor | Loaded language ("provocations", "destabilize"); no US quotes |

**Geopolitical Pattern:** *"Coverage splits along alliance lines: US-aligned sources frame freedom-of-navigation as lawful, China-aligned sources frame it as provocation. Regional sources (ASEAN) focus on de-escalation."*

**Balanced Summary:** *"Multiple nations are involved in overlapping territorial claims in the South China Sea. The Philippines has filed a diplomatic protest, China has reasserted its sovereignty claims while calling for bilateral talks, and the US conducted a naval operation in the area citing international maritime law. ASEAN has called for restraint from all parties."*

---

## How the Agents Are "Embedded" (Not Bolted On)

The key distinction for a uni project: these agents aren't optional add-ons. They ARE the app:

1. **No Agent 1 → No content.** The app has no pre-loaded news database. Every piece of content comes from Agent 1's real-time crawling.
2. **No Agent 2 → No differentiation.** Without bias analysis, this is just another news aggregator. Agent 2's output is what makes the app's UI unique — every article card, every comparison view, every summary is shaped by Agent 2.
3. **The orchestrator IS the backend.** The main API endpoint is essentially: receive query → run Agent 1 → run Agent 2 → stream results. The agents aren't called from a sidebar; they're the main pipeline.

This means in your uni project write-up you can argue:
- The agents are **architecturally embedded** (they are the data pipeline, not a feature flag)
- They demonstrate **autonomous behavior** (Agent 1 decides what to search, Agent 2 decides what counts as bias)
- They use **tool use** (Agent 1 uses search APIs and scrapers as tools; Agent 2 uses the source registry as a knowledge base)
- They form an **agent chain** (output of Agent 1 feeds directly into Agent 2)