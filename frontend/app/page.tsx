"use client";

import { useCallback, useState } from "react";
import ArticleCard from "@/components/ArticleCard";
import BiasReportPanel from "@/components/BiasReportPanel";
import SearchBar from "@/components/SearchBar";
import {
  Article,
  ArticleBiasAnalysis,
  BiasReport,
  streamSearch,
} from "@/lib/streamClient";

type Status = "idle" | "streaming" | "done" | "error";

export default function HomePage() {
  const [status, setStatus] = useState<Status>("idle");
  const [articles, setArticles] = useState<Article[]>([]);
  const [analyses, setAnalyses] = useState<Map<string, ArticleBiasAnalysis>>(
    new Map()
  );
  const [biasReport, setBiasReport] = useState<BiasReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (query: string) => {
    setStatus("streaming");
    setArticles([]);
    setAnalyses(new Map());
    setBiasReport(null);
    setError(null);

    try {
      for await (const event of streamSearch(query)) {
        if (event.type === "article") {
          setArticles((prev) => [...prev, event.data]);
        } else if (event.type === "bias_report") {
          setBiasReport(event.data);
          const map = new Map<string, ArticleBiasAnalysis>();
          for (const a of event.data.per_article) {
            map.set(a.article_url, a);
          }
          setAnalyses(map);
        }
      }
      setStatus("done");
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not reach the backend. Is it running on port 8000?"
      );
      setStatus("error");
    }
  }, []);

  const isSearching = status === "streaming";

  return (
    <main className="min-h-screen flex flex-col items-center px-4 py-12 gap-10">
      <header className="text-center">
        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900">
          The Lighthouse
        </h1>
        <p className="mt-2 text-gray-500 text-lg">
          Read the news. See the framing.
        </p>
      </header>

      <SearchBar onSearch={handleSearch} disabled={isSearching} />

      {isSearching && articles.length === 0 && (
        <p className="text-gray-400 animate-pulse">Crawling news sources…</p>
      )}

      {status === "error" && error && (
        <div
          role="alert"
          className="w-full max-w-2xl rounded-xl border border-red-200 bg-red-50 p-4 text-red-700 text-sm"
        >
          <strong>Error: </strong>
          {error}
        </div>
      )}

      {articles.length > 0 && (
        <section className="w-full max-w-5xl flex flex-col gap-4">
          <h2 className="text-base font-semibold text-gray-500">
            {articles.length} article{articles.length !== 1 ? "s" : ""} found
            {isSearching && " — streaming…"}
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {articles.map((article) => (
              <ArticleCard
                key={article.url}
                article={article}
                analysis={analyses.get(article.url)}
              />
            ))}
          </div>
        </section>
      )}

      {biasReport && (
        <section className="w-full max-w-5xl">
          <BiasReportPanel report={biasReport} />
        </section>
      )}
    </main>
  );
}
