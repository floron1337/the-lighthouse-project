"use client";

import {
  CheckCircle2,
  Compass,
  GitCompareArrows,
  Globe2,
  ScrollText,
  Sparkles,
} from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Article, BiasReport } from "@/lib/streamClient";
import { cn, countryFlag } from "@/lib/utils";
import { SentimentChart } from "@/components/SentimentChart";
import { BiasSpectrum } from "@/components/BiasSpectrum";
import { PoliticalCompass } from "@/components/PoliticalCompass";

interface BiasReportPanelProps {
  report: BiasReport;
  articles: Article[];
}

export default function BiasReportPanel({
  report,
  articles,
}: BiasReportPanelProps) {
  const articleBySource = new Map(articles.map((a) => [a.url, a]));

  return (
    <Card className="overflow-hidden border-accent/30">
      <CardHeader className="bg-gradient-to-br from-accent/10 via-card to-card border-b">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground font-medium">
              <Sparkles className="h-3.5 w-3.5 text-accent" />
              AI Bias Analysis
            </div>
            <CardTitle className="text-2xl font-display">
              {report.topic}
            </CardTitle>
            <CardDescription>
              {report.per_article.length} sources analyzed across{" "}
              {new Set(articles.map((a) => a.country)).size} countries
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <Tabs defaultValue="summary" className="w-full">
          <div className="px-6 pt-5">
            <TabsList className="grid w-full grid-cols-4 max-w-2xl">
              <TabsTrigger value="summary">Summary</TabsTrigger>
              <TabsTrigger value="spectrum">Spectrum</TabsTrigger>
              <TabsTrigger value="patterns">Patterns</TabsTrigger>
              <TabsTrigger value="methodology">Method</TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="summary" className="px-6 pb-6 mt-5 space-y-6">
            <section>
              <SectionHeader
                icon={<ScrollText className="h-4 w-4" />}
                label="Balanced Summary"
                hint="Generated neutral synthesis"
              />
              <p className="mt-3 text-base leading-relaxed text-foreground/90 text-balance">
                {report.balanced_summary}
              </p>
            </section>

            {report.consensus_facts.length > 0 && (
              <section>
                <SectionHeader
                  icon={<CheckCircle2 className="h-4 w-4" />}
                  label="Consensus Facts"
                  hint={`Reported by most sources`}
                />
                <ul className="mt-3 grid gap-2 sm:grid-cols-2">
                  {report.consensus_facts.map((fact, i) => (
                    <li
                      key={i}
                      className="flex gap-2 rounded-lg border bg-bias-neutral/5 px-3 py-2 text-sm"
                    >
                      <CheckCircle2 className="h-4 w-4 text-bias-neutral mt-0.5 shrink-0" />
                      <span className="text-foreground/90">{fact}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </TabsContent>

          <TabsContent value="spectrum" className="px-6 pb-6 mt-5 space-y-8">
            <section>
              <SectionHeader
                icon={<Globe2 className="h-4 w-4" />}
                label="Bias Spectrum"
                hint="Each source plotted by inferred alignment"
              />
              <div className="mt-4">
                <BiasSpectrum
                  analyses={report.per_article}
                  articleBySource={articleBySource}
                />
              </div>
            </section>

            <Separator />

            <section>
              <SectionHeader
                icon={<Compass className="h-4 w-4" />}
                label="Political Compass"
                hint="Economic ↔ social placement per source"
              />
              <div className="mt-4">
                <PoliticalCompass
                  analyses={report.per_article}
                  articleBySource={articleBySource}
                />
              </div>
            </section>

            <Separator />

            <section>
              <SectionHeader
                icon={<Sparkles className="h-4 w-4" />}
                label="Sentiment by Source"
                hint="−1 (negative) → +1 (positive)"
              />
              <div className="mt-4">
                <SentimentChart
                  analyses={report.per_article}
                  articleBySource={articleBySource}
                />
              </div>
            </section>
          </TabsContent>

          <TabsContent value="patterns" className="px-6 pb-6 mt-5 space-y-6">
            {report.disputed_framings.length > 0 && (
              <section>
                <SectionHeader
                  icon={<GitCompareArrows className="h-4 w-4" />}
                  label="Disputed Framings"
                  hint="Same event, different angles"
                />
                <div className="mt-3 grid gap-3">
                  {report.disputed_framings.map((item, i) => (
                    <div
                      key={i}
                      className="rounded-lg border bg-card/50 p-4 hover:border-accent/40 transition-colors"
                    >
                      <p className="font-medium text-foreground">
                        “{item.framing}”
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-muted-foreground">
                        <Badge variant="mixed" className="font-normal">
                          {item.geopolitical_pattern}
                        </Badge>
                        {item.sources_using_it.length > 0 && (
                          <span>
                            Used by:{" "}
                            <span className="text-foreground/80 font-medium">
                              {item.sources_using_it.join(", ")}
                            </span>
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {report.geopolitical_patterns.length > 0 && (
              <section>
                <SectionHeader
                  icon={<Globe2 className="h-4 w-4" />}
                  label="Geopolitical Patterns"
                  hint="Cross-source observations"
                />
                <ul className="mt-3 space-y-2">
                  {report.geopolitical_patterns.map((p, i) => (
                    <li
                      key={i}
                      className="flex gap-3 rounded-lg border-l-2 border-accent/60 bg-accent/5 px-4 py-3 text-sm"
                    >
                      <span className="text-foreground/90 leading-relaxed">
                        {p}
                      </span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </TabsContent>

          <TabsContent value="methodology" className="px-6 pb-6 mt-5">
            <section>
              <SectionHeader
                icon={<ScrollText className="h-4 w-4" />}
                label="Methodology"
                hint="Transparency note"
              />
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">
                {report.methodology_note}
              </p>
              <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <Stat label="Sources" value={report.per_article.length} />
                <Stat
                  label="Countries"
                  value={new Set(articles.map((a) => a.country)).size}
                />
                <Stat
                  label="Disputed framings"
                  value={report.disputed_framings.length}
                />
                <Stat
                  label="Consensus facts"
                  value={report.consensus_facts.length}
                />
              </div>
            </section>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

function SectionHeader({
  icon,
  label,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  hint?: string;
}) {
  return (
    <div className="flex items-baseline justify-between gap-2 border-b pb-2">
      <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wider text-foreground">
        <span className="text-accent">{icon}</span>
        {label}
      </h3>
      {hint && (
        <span className="text-xs text-muted-foreground">{hint}</span>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border bg-card/60 px-3 py-2.5">
      <div className="text-2xl font-display font-semibold text-foreground tabular-nums">
        {value}
      </div>
      <div className="text-xs text-muted-foreground mt-0.5">{label}</div>
    </div>
  );
}

export function SourceFlag({ country }: { country: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-flex h-6 w-6 items-center justify-center rounded-full bg-muted text-base"
          )}
          aria-label={country}
        >
          {countryFlag(country)}
        </span>
      </TooltipTrigger>
      <TooltipContent>{country}</TooltipContent>
    </Tooltip>
  );
}
