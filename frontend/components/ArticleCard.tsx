import { ExternalLink, ChevronDown, AlertCircle, Quote } from "lucide-react";
import { Article, ArticleBiasAnalysis } from "@/lib/streamClient";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn, countryFlag } from "@/lib/utils";

interface ArticleCardProps {
  article: Article;
  analysis?: ArticleBiasAnalysis;
}

type BiasVariant =
  | "west"
  | "brics"
  | "neutral"
  | "government"
  | "mixed"
  | "outline";

function biasVariant(direction?: string): BiasVariant {
  if (!direction) return "outline";
  const d = direction.toLowerCase();
  if (d.includes("west")) return "west";
  if (d.includes("brics") || d.includes("east")) return "brics";
  if (d.includes("neutral")) return "neutral";
  if (d.includes("government") || d.includes("state")) return "government";
  return "mixed";
}

function sentimentMeta(score: number) {
  if (score > 0.25)
    return { label: "Positive", color: "bg-bias-neutral", text: "text-bias-neutral" };
  if (score < -0.25)
    return { label: "Negative", color: "bg-bias-brics", text: "text-bias-brics" };
  return { label: "Neutral", color: "bg-muted-foreground", text: "text-muted-foreground" };
}

export default function ArticleCard({ article, analysis }: ArticleCardProps) {
  const variant = biasVariant(analysis?.overall_bias_direction);
  const sentiment = analysis ? sentimentMeta(analysis.sentiment_score) : null;

  return (
    <Card className="group relative flex flex-col overflow-hidden hover:shadow-md hover:border-accent/40 transition-all duration-200 animate-fade-in">
      <span
        aria-hidden="true"
        className={cn(
          "absolute left-0 top-0 h-full w-1",
          variant === "west" && "bg-bias-west",
          variant === "brics" && "bg-bias-brics",
          variant === "neutral" && "bg-bias-neutral",
          variant === "government" && "bg-bias-government",
          variant === "mixed" && "bg-bias-mixed",
          variant === "outline" && "bg-border"
        )}
      />

      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-2 text-xs text-muted-foreground">
          <div className="flex items-center gap-2 min-w-0">
            <span className="text-base leading-none" aria-hidden="true">
              {countryFlag(article.country)}
            </span>
            <span className="font-semibold text-foreground truncate">
              {article.source_name}
            </span>
            <span className="text-muted-foreground/60">·</span>
            <span className="uppercase tracking-wide">{article.country}</span>
          </div>
          <time dateTime={article.published_at} className="shrink-0">
            {new Date(article.published_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
            })}
          </time>
        </div>

        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "mt-2 inline-flex items-start gap-1.5 group/link",
            "text-lg font-semibold leading-snug font-display",
            "text-foreground hover:text-accent transition-colors text-balance"
          )}
        >
          <span className="flex-1">{article.title}</span>
          <ExternalLink
            className="h-4 w-4 mt-1 shrink-0 opacity-0 group-hover/link:opacity-100 transition-opacity"
            aria-hidden="true"
          />
          <span className="sr-only">(opens in new tab)</span>
        </a>
      </CardHeader>

      <CardContent className="flex-1 flex flex-col gap-4 pb-5">
        {article.full_text && (
          <p className="text-sm text-muted-foreground line-clamp-3 leading-relaxed">
            {article.full_text}
          </p>
        )}

        {analysis ? (
          <>
            <Separator />

            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={variant === "outline" ? "outline" : variant}>
                {analysis.overall_bias_direction}
              </Badge>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground cursor-default">
                    <span className="w-12">
                      <Progress
                        value={Math.round(analysis.confidence * 100)}
                        className="h-1.5"
                        indicatorClassName="bg-accent"
                      />
                    </span>
                    {Math.round(analysis.confidence * 100)}%
                  </span>
                </TooltipTrigger>
                <TooltipContent>Model confidence in this assessment</TooltipContent>
              </Tooltip>
              {sentiment && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className={cn("inline-flex items-center gap-1 text-xs cursor-default", sentiment.text)}>
                      <span className={cn("h-1.5 w-1.5 rounded-full", sentiment.color)} />
                      {sentiment.label} {analysis.sentiment_score > 0 ? "+" : ""}
                      {analysis.sentiment_score.toFixed(2)}
                    </span>
                  </TooltipTrigger>
                  <TooltipContent>Sentiment score (−1 to +1)</TooltipContent>
                </Tooltip>
              )}
            </div>

            <details className="text-sm group/details">
              <summary
                className={cn(
                  "flex items-center gap-1 cursor-pointer select-none list-none",
                  "text-xs font-medium text-accent hover:text-accent/80"
                )}
              >
                <ChevronDown className="h-3.5 w-3.5 transition-transform group-open/details:rotate-180" />
                Why was this flagged?
              </summary>
              <div className="mt-3 flex flex-col gap-3 text-sm text-foreground/90 border-l-2 border-accent/30 pl-3">
                <p className="leading-relaxed">{analysis.framing_analysis}</p>

                {analysis.loaded_terms.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                      <Quote className="h-3 w-3" />
                      Loaded terms
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {analysis.loaded_terms.map((term) => (
                        <span
                          key={term}
                          className="text-xs px-2 py-0.5 rounded-md bg-bias-mixed/15 text-bias-mixed font-medium"
                        >
                          {term}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {analysis.omissions.length > 0 && (
                  <div className="space-y-1">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1">
                      <AlertCircle className="h-3 w-3" />
                      Possible omissions
                    </p>
                    <ul className="space-y-1 text-sm text-foreground/80">
                      {analysis.omissions.map((o, i) => (
                        <li key={i} className="flex gap-2">
                          <span className="text-muted-foreground">·</span>
                          <span>{o}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </details>
          </>
        ) : (
          <div className="flex items-center gap-2 text-xs text-muted-foreground/80">
            <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
            Awaiting bias analysis…
          </div>
        )}
      </CardContent>
    </Card>
  );
}
