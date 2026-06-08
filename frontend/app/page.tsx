"use client";

import dynamic from "next/dynamic";
import { useCallback, useMemo, useState } from "react";
import { Lightbulb, Loader2, Newspaper, AlertCircle } from "lucide-react";
import ArticleCard from "@/components/ArticleCard";
import BiasReportPanel from "@/components/BiasReportPanel";
import SearchBar from "@/components/SearchBar";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card, CardContent } from "@/components/ui/card";
import {
  Article,
  ArticleBiasAnalysis,
  BiasReport,
  streamSearch,
} from "@/lib/streamClient";

const RegionMap = dynamic(() => import("@/components/RegionMap"), {
  ssr: false,
  loading: () => (
    <div className="h-[460px] rounded-xl border bg-card flex items-center justify-center text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Loading map…
    </div>
  ),
});

type Status = "idle" | "streaming" | "done" | "error";

export default function HomePage() {
  const [status, setStatus] = useState<Status>("idle");
  const [query, setQuery] = useState<string>("");
  const [articles, setArticles] = useState<Article[]>([]);
  const [analyses, setAnalyses] = useState<Map<string, ArticleBiasAnalysis>>(
    new Map()
  );
  const [biasReport, setBiasReport] = useState<BiasReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (q: string) => {
    setStatus("streaming");
    setQuery(q);
    setArticles([]);
    setAnalyses(new Map());
    setBiasReport(null);
    setError(null);

    try {
      for await (const event of streamSearch(q)) {
        if (event.type === "article") {
          setArticles((prev) => [...prev, event.data]);
        } else if (event.type === "article_analysis") {
          setAnalyses((prev) => {
            const next = new Map(prev);
            next.set(event.data.article_url, event.data);
            return next;
          });
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
  const hasResults = articles.length > 0;

  const stats = useMemo(() => {
    const countries = new Set(articles.map((a) => a.country)).size;
    return { articles: articles.length, countries };
  }, [articles]);

  return (
    <main className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-30 border-b bg-background/80 backdrop-blur-md">
        <div className="container flex h-16 items-center justify-between">
          <a href="/" className="flex items-center gap-2.5 group">
            <span className="grid h-9 w-9 place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm group-hover:rotate-3 transition-transform">
              <Lightbulb className="h-5 w-5" />
            </span>
            <span className="flex flex-col leading-none">
              <span className="font-display font-semibold text-lg tracking-tight">
                The Lighthouse
              </span>
              <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground mt-0.5">
                Bias-aware news
              </span>
            </span>
          </a>
          <nav className="flex items-center gap-3">
            <a
              href="https://linear.app/the-lighthouse-project"
              target="_blank"
              rel="noopener noreferrer"
              className="hidden sm:inline-flex text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              About
            </a>
            <ThemeToggle />
          </nav>
        </div>
      </header>

      <section className="relative">
        <div className="absolute inset-0 gradient-radial pointer-events-none" />
        <div className="container relative flex flex-col items-center text-center pt-16 pb-10 gap-6">
          <span className="inline-flex items-center gap-2 rounded-full border bg-card/60 px-3 py-1 text-xs text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-bias-neutral animate-pulse" />
            Two AI agents · 20+ international sources · streaming bias analysis
          </span>
          <h1 className="font-display text-4xl sm:text-5xl md:text-6xl font-semibold tracking-tight text-balance max-w-3xl">
            Read the news.{" "}
            <span className="text-accent italic">See the framing.</span>
          </h1>
          <p className="text-base sm:text-lg text-muted-foreground max-w-2xl text-balance">
            Search any topic. We crawl articles from across the geopolitical
            spectrum and show you how each source frames the same story —
            side by side.
          </p>
          <div className="w-full flex justify-center mt-2">
            <SearchBar onSearch={handleSearch} disabled={isSearching} />
          </div>
        </div>
      </section>

      <div className="container flex flex-col gap-10 pb-24">
        {status === "error" && error && (
          <Card className="border-destructive/30 bg-destructive/5">
            <CardContent className="flex items-start gap-3 p-4 text-sm text-destructive-foreground/90">
              <AlertCircle className="h-5 w-5 shrink-0 text-destructive" />
              <div>
                <p className="font-semibold text-destructive">Couldn’t complete that search</p>
                <p className="text-foreground/80 mt-0.5">{error}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {isSearching && articles.length === 0 && (
          <CrawlSkeleton />
        )}

        {hasResults && (
          <>
            <RegionMap articles={articles} />

            <section className="flex flex-col gap-4">
              <header className="flex items-end justify-between gap-3 border-b pb-3">
                <div>
                  <h2 className="font-display text-2xl font-semibold tracking-tight">
                    Coverage
                  </h2>
                  <p className="text-sm text-muted-foreground mt-1">
                    <span className="font-medium text-foreground">
                      {stats.articles}
                    </span>{" "}
                    article{stats.articles !== 1 ? "s" : ""} from{" "}
                    <span className="font-medium text-foreground">
                      {stats.countries}
                    </span>{" "}
                    {stats.countries !== 1 ? "countries" : "country"}
                    {query && (
                      <>
                        {" "}· topic:{" "}
                        <span className="font-medium text-foreground">
                          {query}
                        </span>
                      </>
                    )}
                  </p>
                </div>
                {isSearching && (
                  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    Streaming…
                  </span>
                )}
              </header>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {articles.map((article) => (
                  <ArticleCard
                    key={article.url}
                    article={article}
                    analysis={analyses.get(article.url)}
                  />
                ))}
              </div>
            </section>

            {biasReport && (
              <section className="animate-fade-in">
                <BiasReportPanel report={biasReport} articles={articles} />
              </section>
            )}
          </>
        )}

        {status === "idle" && <EmptyState />}
      </div>

      <footer className="border-t mt-auto">
        <div className="container flex flex-col sm:flex-row items-center justify-between gap-3 py-6 text-xs text-muted-foreground">
          <span>
            © {new Date().getFullYear()} The Lighthouse · A university project
            on bias-aware news.
          </span>
          <span className="flex items-center gap-1.5">
            <Lightbulb className="h-3.5 w-3.5 text-accent" />
            Powered by Claude · NewsAPI · GNews
          </span>
        </div>
      </footer>
    </main>
  );
}

function EmptyState() {
  return (
    <Card className="border-dashed">
      <CardContent className="p-10 flex flex-col items-center text-center gap-3">
        <Newspaper className="h-10 w-10 text-muted-foreground/60" />
        <h3 className="font-display text-xl">Ask anything that’s in the news.</h3>
        <p className="text-sm text-muted-foreground max-w-md">
          Two AI agents will fetch articles from across the geopolitical
          spectrum and analyze how each source frames the story.
        </p>
      </CardContent>
    </Card>
  );
}

function CrawlSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="animate-pulse">
          <CardContent className="space-y-3 p-5">
            <div className="h-3 w-1/3 rounded bg-muted" />
            <div className="h-5 w-full rounded bg-muted" />
            <div className="h-5 w-4/5 rounded bg-muted" />
            <div className="h-3 w-full rounded bg-muted/70" />
            <div className="h-3 w-2/3 rounded bg-muted/70" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
