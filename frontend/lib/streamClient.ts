// Types mirror the Pydantic models defined in backend/app/models/

export interface Article {
  title: string;
  full_text: string;
  url: string;
  source_id: string;
  source_name: string;
  country: string;
  published_at: string; // ISO 8601 datetime string
  author: string | null;
  language: string;
  translated_text: string | null;
}

export interface PoliticalCompassPoint {
  economic_axis: number;
  social_axis: number;
  regional_context: string;
  label: string;
  confidence: number;
}

export interface ArticleBiasAnalysis {
  article_url: string;
  source_id: string;
  overall_bias_direction: string;
  confidence: number;
  framing_analysis: string;
  loaded_terms: string[];
  omissions: string[];
  sentiment_score: number;
  attribution_balance: string;
  political_compass?: PoliticalCompassPoint | null;
}

export interface DisputedFraming {
  framing: string;
  sources_using_it: string[];
  geopolitical_pattern: string;
}

export interface BiasReport {
  topic: string;
  consensus_facts: string[];
  disputed_framings: DisputedFraming[];
  per_article: ArticleBiasAnalysis[];
  geopolitical_patterns: string[];
  balanced_summary: string;
  methodology_note: string;
}

export type SearchEvent =
  | { type: "article"; data: Article }
  | { type: "article_analysis"; data: ArticleBiasAnalysis }
  | { type: "bias_report"; data: BiasReport };

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

/**
 * Streams SSE events from POST /api/search.
 *
 * Yields SearchEvent objects as they arrive: article events, progressive
 * article_analysis events, then a single bias_report event. The caller receives events one by one via
 * `for await (const event of streamSearch(query)) { ... }`.
 *
 * Throws if the backend is unreachable or returns a non-2xx status.
 */
export async function* streamSearch(
  query: string
): AsyncGenerator<SearchEvent> {
  const response = await fetch(`${BACKEND_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    throw new Error(
      `Backend returned ${response.status} — is it running on ${BACKEND_URL}?`
    );
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("Response body is not readable");

  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const raw = line.slice(6).trim();
      if (raw === "[DONE]") return;
      yield JSON.parse(raw) as SearchEvent;
    }
  }
}
