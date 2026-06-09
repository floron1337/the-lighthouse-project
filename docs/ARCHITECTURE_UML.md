# Lighthouse — Architecture Diagrams

> Backlog: [Lighthouse on Linear](https://linear.app/the-lighthouse-project/project/lighthouse-news-bias-report-d2f5d9dca425/overview)
> · See also [`../DESIGN.md`](../DESIGN.md)

Diagrams are stored as PNG files in [`diagrams/`](diagrams/) and embedded below. To regenerate after editing a source block, run:

```bash
npx @mermaid-js/mermaid-cli -i input.mmd -o docs/diagrams/name.png -w 1400 -b white
```

---

## 1. System topology — component diagram

The app is a browser → Next.js → FastAPI stack. The two AI agents live inside the FastAPI backend and are chained by the orchestrator. All LLM inference runs locally via Ollama.

![Component diagram](diagrams/component.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart LR
  subgraph Browser
    UI["Next.js UI\nSearchBar · ArticleCard\nBiasReportPanel · RegionMap"]
    SC["streamClient.ts\nSSE + AbortController"]
    UI --> SC
  end

  subgraph Backend["FastAPI Backend"]
    API["/api/search\nSSE endpoint"]
    ORCH["Orchestrator\nprocess_query()"]
    subgraph A1["Agent 1 — News Crawler"]
      QE["QueryExpander\n(LLM)"]
      SEARCH["Searchers\nNewsAPI · GNews"]
      EXT["Extractor + Dedupe\ntrafilatura · TF-IDF"]
    end
    subgraph A2["Agent 2 — Bias Analyst"]
      AA["ArticleAnalyzer\n(LLM, json_mode)"]
      CMP["Comparator\n(LLM + deterministic)"]
    end
    LLM[("Ollama\nllama3.2\nlocalhost:11434")]
  end

  subgraph External
    NAPI["NewsAPI.org"]
    GNEWS["GNews"]
    ATLAS["world-atlas\nTopoJSON CDN"]
  end

  SC -- "POST /api/search" --> API
  API --> ORCH
  ORCH --> A1
  ORCH --> A2
  QE --> LLM
  AA --> LLM
  CMP --> LLM
  SEARCH --> NAPI
  SEARCH --> GNEWS
  UI -. "map geometries" .-> ATLAS
```

</details>

---

## 2. Domain model — class diagram

Mirrors the Pydantic models in `backend/app/models/` and the TypeScript interfaces in `frontend/lib/streamClient.ts`.

![Class diagram](diagrams/class.png)

<details>
<summary>Mermaid source</summary>

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
    +PoliticalCompassPoint compass
  }

  class BiasReport {
    +str topic
    +List~str~ consensus_facts
    +List~dict~ disputed_framings
    +List~ArticleBiasAnalysis~ per_article
    +List~str~ geopolitical_patterns
    +str balanced_summary
    +str methodology_note
  }

  ArticleBundle "1" o-- "*" Article
  Article --> Source : source_id
  BiasReport "1" o-- "*" ArticleBiasAnalysis
  ArticleBiasAnalysis --> Article : article_url
```

</details>

---

## 3. End-to-end flow — sequence diagram

From keystroke to fully rendered UI: SSE stream, both agents, progressive hydration.

![Sequence diagram](diagrams/sequence.png)

<details>
<summary>Mermaid source</summary>

```mermaid
sequenceDiagram
  autonumber
  actor User
  participant UI as Next.js UI
  participant SC as streamClient
  participant API as FastAPI
  participant ORCH as Orchestrator
  participant A1 as Crawler Agent
  participant A2 as Bias Agent
  participant LLM as Ollama
  participant SRC as News APIs

  User->>UI: submit query
  UI->>SC: streamSearch(query)
  SC->>API: POST /api/search
  API->>ORCH: process_query(query)

  rect rgb(235,245,255)
    Note over A1: Agent 1 — Crawler
    ORCH->>A1: iter_articles(query)
    A1->>LLM: expand query
    LLM-->>A1: sub-queries
    par per sub-query
      A1->>SRC: NewsAPI + GNews
      SRC-->>A1: articles
    end
    A1->>A1: trafilatura + TF-IDF dedupe
    loop each article
      A1-->>ORCH: yield Article
      ORCH-->>SC: SSE: article
      SC-->>UI: render ArticleCard
    end
    ORCH-->>SC: SSE: crawl_done
    SC-->>UI: status = analyzing
  end

  rect rgb(255,245,235)
    Note over A2: Agent 2 — Bias Analyst
    par per article (concurrency=2)
      ORCH->>A2: analyze_article
      A2->>LLM: bias prompt json_mode
      LLM-->>A2: ArticleBiasAnalysis
      A2-->>ORCH: analysis
      ORCH-->>SC: SSE: article_analysis
      SC-->>UI: badge ArticleCard
    end
    ORCH->>A2: final_report
    A2->>LLM: compare prompt
    LLM-->>A2: BiasReport
    ORCH-->>SC: SSE: bias_report
    SC-->>UI: BiasReportPanel
  end

  UI-->>User: complete
```

</details>

---

## 4. React component tree — frontend diagram

How the Next.js components compose and which data each consumes.

![Frontend component diagram](diagrams/frontend.png)

<details>
<summary>Mermaid source</summary>

```mermaid
flowchart TB
  Layout["layout.tsx\nThemeProvider · TooltipProvider"]
  Page["page.tsx\nstatus · articles · analyses\nbiasReport · selectedCountry"]
  Layout --> Page

  Page --> Header
  Page --> Search["SearchBar\nAnalyze / Stop button"]
  Page --> Map["RegionMap\ncountry-click filter"]
  Page --> Cards["ArticleCard x N\nbias badge overlay"]
  Page --> Report["BiasReportPanel"]

  subgraph Header
    Logo
    Toggle["ThemeToggle"]
  end

  subgraph Report["BiasReportPanel Tabs"]
    Summary["Summary"]
    Spectrum["Spectrum\nBiasSpectrum · SentimentChart"]
    Patterns["Patterns"]
    Method["Methodology"]
    Compass["Political Compass"]
  end

  Cards -. "open article" .-> External["Original article\nnew tab"]
  Map -. "fetch" .-> Atlas["world-atlas TopoJSON"]
```

</details>

---

## 5. Search lifecycle — state machine

Frontend status transitions driven by SSE events from the backend.

![State machine](diagrams/state.png)

<details>
<summary>Mermaid source</summary>

```mermaid
stateDiagram-v2
  [*] --> Idle
  Idle --> Streaming : user submits query
  Streaming --> Streaming : article event
  Streaming --> Analyzing : crawl_done event
  Analyzing --> Analyzing : article_analysis event
  Analyzing --> Done : bias_report received
  Streaming --> Error : network or backend error
  Analyzing --> Done : 180s safety-net timeout
  Error --> Streaming : user retries
  Done --> Streaming : new query
  Done --> Idle : page reload
  Streaming --> Idle : Stop button
  Analyzing --> Idle : Stop button
```

</details>
