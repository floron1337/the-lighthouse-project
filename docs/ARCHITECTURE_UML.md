# Lighthouse — Architecture UML

This document captures the system architecture of the Lighthouse News Bias
Report app as a set of UML diagrams. All diagrams use Mermaid so they
render natively on GitHub and in most Markdown viewers.

> Source of truth: [Lighthouse News Bias Report on Linear](https://linear.app/the-lighthouse-project/project/lighthouse-news-bias-report-d2f5d9dca425/overview)
> · See also [`../DESIGN.md`](../DESIGN.md).

---

## 1. Component diagram — system topology

The app is a thin browser → Next.js → FastAPI → external-tool stack. The
two AI agents live inside the FastAPI backend and are chained by the
orchestrator.

```mermaid
flowchart LR
  subgraph Browser["🌐 Browser"]
    UI["Next.js UI<br/>(SearchBar · ArticleCard · BiasReportPanel · RegionMap)"]
    SC["streamClient.ts<br/>(SSE reader)"]
    UI --> SC
  end

  subgraph Backend["🐍 FastAPI Backend"]
    API["/api/search<br/>SSE endpoint/"]
    ORCH["Orchestrator<br/>process_query()"]
    subgraph A1["Agent 1 — News Crawler"]
      QE[QueryExpander]
      SR[SourceRegistry]
      SEARCH[Searchers<br/>NewsAPI · GNews · RSS]
      EXT[Extractor + Dedupe]
    end
    subgraph A2["Agent 2 — Bias Analyst"]
      SP[SourceProfiler]
      AA[ArticleAnalyzer]
      CMP[Comparator]
    end
    LLM[(LLM Service<br/>Anthropic / OpenAI)]
    CACHE[(Cache)]
  end

  subgraph External["☁️ External"]
    NAPI[NewsAPI.org]
    GNEWS[GNews]
    RSS[RSS Feeds]
    ATLAS[world-atlas TopoJSON CDN]
  end

  SC -- "POST /api/search" --> API
  API --> ORCH
  ORCH --> A1
  ORCH --> A2
  A1 --> EXT
  QE --> LLM
  AA --> LLM
  CMP --> LLM
  SP --> SR
  SEARCH --> NAPI
  SEARCH --> GNEWS
  SEARCH --> RSS
  ORCH --> CACHE
  UI -. "fetches map geometries" .-> ATLAS
```

---

## 2. Class diagram — domain model

Mirrors the dataclasses defined in `backend/app/models/` and the
TypeScript interfaces in `frontend/lib/streamClient.ts`.

```mermaid
classDiagram
  direction LR

  class Article {
    +str title
    +str full_text
    +str url
    +str source_id
    +str source_name
    +str country
    +datetime published_at
    +Optional~str~ author
    +str language
    +Optional~str~ translated_text
  }

  class ArticleBundle {
    +str query
    +List~Article~ articles
    +List~str~ sources_covered
    +List~str~ countries_covered
    +datetime crawl_timestamp
  }

  class Source {
    +str id
    +str name
    +str country
    +str region
    +str ownership
    +str known_lean
    +str alliance_bloc
    +str rss_url
    +str language
    +float credibility_score
  }

  class ArticleBiasAnalysis {
    +str article_url
    +str source_id
    +str overall_bias_direction
    +float confidence
    +str framing_analysis
    +List~str~ loaded_terms
    +List~str~ omissions
    +float sentiment_score
    +str attribution_balance
  }

  class DisputedFraming {
    +str framing
    +List~str~ sources_using_it
    +str geopolitical_pattern
  }

  class BiasReport {
    +str topic
    +List~str~ consensus_facts
    +List~DisputedFraming~ disputed_framings
    +List~ArticleBiasAnalysis~ per_article
    +List~str~ geopolitical_patterns
    +str balanced_summary
    +str methodology_note
  }

  ArticleBundle "1" o-- "*" Article
  Article --> Source : source_id
  BiasReport "1" o-- "*" ArticleBiasAnalysis
  BiasReport "1" o-- "*" DisputedFraming
  ArticleBiasAnalysis --> Article : article_url
```

---

## 3. Sequence diagram — a single user query

End-to-end: keystroke → SSE stream → both agents → progressive UI
hydration.

```mermaid
sequenceDiagram
  autonumber
  actor User
  participant UI as Next.js UI
  participant SC as streamClient
  participant API as FastAPI /api/search
  participant ORCH as Orchestrator
  participant A1 as Crawler Agent
  participant A2 as Bias Agent
  participant LLM
  participant SRC as News Sources

  User->>UI: type "South China Sea tensions"
  UI->>SC: streamSearch(query)
  SC->>API: POST /api/search { query }
  API->>ORCH: process_query(query)

  rect rgb(245, 245, 250)
    note over A1: Agent 1 — Crawler
    ORCH->>A1: search(query)
    A1->>LLM: expand(query)
    LLM-->>A1: sub-queries
    par per source
      A1->>SRC: REST / RSS fetch
      SRC-->>A1: articles
    end
    A1->>A1: extract + dedupe
    loop each article
      A1-->>ORCH: yield Article
      ORCH-->>API: SSE: {type:"article"}
      API-->>SC: data: {...}
      SC-->>UI: render ArticleCard
    end
  end

  rect rgb(250, 245, 240)
    note over A2: Agent 2 — Bias Analyst
    ORCH->>A2: analyze(bundle)
    loop each article
      A2->>LLM: analyze with source profile
      LLM-->>A2: ArticleBiasAnalysis
    end
    A2->>LLM: compare + summarize
    LLM-->>A2: BiasReport
    A2-->>ORCH: BiasReport
    ORCH-->>API: SSE: {type:"bias_report"}
    API-->>SC: data: {...}
    SC-->>UI: render BiasReportPanel + RegionMap highlights
  end

  UI-->>User: streamed cards + bias spectrum + summary
```

---

## 4. Frontend component diagram

How the React components compose, and which data they consume.

```mermaid
flowchart TB
  Layout["app/layout.tsx<br/>ThemeProvider · TooltipProvider"]
  Page["app/page.tsx<br/>(state: articles, analyses, biasReport)"]
  Layout --> Page

  Page --> Header
  Page --> Search["SearchBar"]
  Page --> Map["RegionMap (dynamic, ssr:false)"]
  Page --> Cards["ArticleCard[]"]
  Page --> Report["BiasReportPanel"]

  subgraph Header
    Logo
    Toggle["ThemeToggle<br/>(next-themes · localStorage)"]
  end

  subgraph Report["BiasReportPanel (Tabs)"]
    Summary["Summary tab"]
    Spectrum["Spectrum tab → BiasSpectrum + SentimentChart (Recharts)"]
    Patterns["Patterns tab"]
    Method["Methodology tab"]
  end

  Cards -. clickable headline .-> External[("Original article<br/>(new tab)")]
  Map -. fetches .-> Atlas[("world-atlas<br/>TopoJSON")]
```

---

## 5. State machine — search lifecycle

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> Streaming : user submits query
  Streaming --> Streaming : article event received
  Streaming --> Done : bias_report event received
  Streaming --> Error : network / 5xx
  Error --> Streaming : user retries
  Done --> Streaming : new query
  Done --> [*]
```
