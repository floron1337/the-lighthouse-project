"use client";

import { Article, ArticleBiasAnalysis } from "@/lib/streamClient";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn, countryFlag } from "@/lib/utils";

interface BiasSpectrumProps {
  analyses: ArticleBiasAnalysis[];
  articleBySource: Map<string, Article>;
}

function biasPosition(direction: string): number {
  const d = direction.toLowerCase();
  if (d.includes("west")) return 15;
  if (d.includes("brics") || d.includes("east")) return 85;
  if (d.includes("government") || d.includes("state")) return 70;
  if (d.includes("neutral")) return 50;
  return 50 + (Math.random() * 10 - 5);
}

function biasColor(direction: string): string {
  const d = direction.toLowerCase();
  if (d.includes("west")) return "bg-bias-west";
  if (d.includes("brics") || d.includes("east")) return "bg-bias-brics";
  if (d.includes("government") || d.includes("state"))
    return "bg-bias-government";
  if (d.includes("neutral")) return "bg-bias-neutral";
  return "bg-bias-mixed";
}

export function BiasSpectrum({
  analyses,
  articleBySource,
}: BiasSpectrumProps) {
  const points = analyses.map((a) => {
    const article = articleBySource.get(a.article_url);
    return {
      analysis: a,
      article,
      position: biasPosition(a.overall_bias_direction),
      color: biasColor(a.overall_bias_direction),
    };
  });

  return (
    <div className="space-y-3">
      <div className="relative h-20">
        <div
          className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-3 rounded-full"
          style={{
            background:
              "linear-gradient(90deg, hsl(var(--bias-west)) 0%, hsl(var(--bias-neutral)) 50%, hsl(var(--bias-brics)) 100%)",
            opacity: 0.25,
          }}
        />
        <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 h-3 rounded-full ring-1 ring-border/60" />

        {points.map((p, i) => {
          const offsetY =
            i % 2 === 0 ? "calc(50% - 28px)" : "calc(50% + 12px)";
          return (
            <Tooltip key={p.analysis.article_url}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="absolute -translate-x-1/2 group"
                  style={{ left: `${p.position}%`, top: offsetY }}
                  aria-label={`${p.article?.source_name ?? p.analysis.source_id}: ${p.analysis.overall_bias_direction}`}
                >
                  <span
                    className={cn(
                      "block h-3.5 w-3.5 rounded-full ring-2 ring-background shadow-md transition-transform group-hover:scale-125",
                      p.color
                    )}
                  />
                  <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 h-3.5 w-3.5 rounded-full opacity-30 animate-ping pointer-events-none" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="text-xs">
                <div className="font-semibold flex items-center gap-1.5">
                  <span>{countryFlag(p.article?.country)}</span>
                  {p.article?.source_name ?? p.analysis.source_id}
                </div>
                <div className="text-muted-foreground capitalize">
                  {p.analysis.overall_bias_direction}
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>

      <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-bias-west" />
          NATO / Western
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-bias-neutral" />
          Neutral
        </span>
        <span className="flex items-center gap-1.5">
          BRICS+ / Eastern
          <span className="h-2 w-2 rounded-full bg-bias-brics" />
        </span>
      </div>
    </div>
  );
}
