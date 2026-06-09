"use client";

import * as React from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Article,
  ArticleBiasAnalysis,
  RegionalAnchor,
} from "@/lib/streamClient";
import { cn, countryFlag } from "@/lib/utils";

interface PoliticalCompassProps {
  analyses: ArticleBiasAnalysis[];
  articleBySource: Map<string, Article>;
  /** When provided, every source is replotted relative to this anchor — the
   * anchor sits at the centre of the chart and source coordinates become
   * (source − anchor). Lets the user view the same compass through a
   * "median citizen of region X" lens. */
  viewAnchor?: RegionalAnchor | null;
}

function dotColor(direction: string): string {
  const d = direction.toLowerCase();
  if (d.includes("west")) return "bg-bias-west";
  if (d.includes("brics") || d.includes("east")) return "bg-bias-brics";
  if (d.includes("government") || d.includes("state"))
    return "bg-bias-government";
  if (d.includes("neutral")) return "bg-bias-neutral";
  return "bg-bias-mixed";
}

// Maps -1..+1 to a 0..100 percent position on the SVG plane.
function toPercent(value: number): number {
  const clamped = Math.max(-1, Math.min(1, value));
  return ((clamped + 1) / 2) * 100;
}

export function PoliticalCompass({
  analyses,
  articleBySource,
  viewAnchor = null,
}: PoliticalCompassProps) {
  const anchorEcon = viewAnchor?.economic_axis ?? 0;
  const anchorSocial = viewAnchor?.social_axis ?? 0;
  const isAnchored = Boolean(viewAnchor && viewAnchor.id !== "global");

  const points = React.useMemo(
    () =>
      analyses
        .filter((a) => a.political_compass)
        .map((a) => {
          const article = articleBySource.get(a.article_url);
          const compass = a.political_compass!;
          return {
            id: a.article_url,
            sourceName: article?.source_name ?? a.source_id,
            country: article?.country ?? "",
            // absolute coordinates, as returned by the LLM
            economic: compass.economic_axis,
            social: compass.social_axis,
            // viewed coordinates — what the user sees on screen
            viewedEconomic: compass.economic_axis - anchorEcon,
            viewedSocial: compass.social_axis - anchorSocial,
            label: compass.label,
            regional: compass.regional_context,
            confidence: compass.confidence,
            direction: a.overall_bias_direction,
          };
        }),
    [analyses, articleBySource, anchorEcon, anchorSocial]
  );

  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-dashed bg-card/60 px-4 py-6 text-center text-sm text-muted-foreground">
        No political-compass data was returned for these sources yet.
      </div>
    );
  }

  return (
    <div className="grid gap-5 md:grid-cols-[1fr_auto] md:items-start">
      <div className="relative aspect-square w-full max-w-[460px] mx-auto rounded-xl border bg-gradient-to-br from-card via-card to-muted/40 shadow-sm">
        {/* quadrant background tints */}
        <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 rounded-xl overflow-hidden">
          <div className="bg-bias-government/[0.05] border-r border-b border-border/60" />
          <div className="bg-bias-brics/[0.05] border-b border-border/60" />
          <div className="bg-bias-west/[0.05] border-r border-border/60" />
          <div className="bg-bias-neutral/[0.05]" />
        </div>

        {/* axis lines */}
        <div className="absolute inset-0">
          <span className="absolute left-1/2 top-0 bottom-0 w-px bg-border" />
          <span className="absolute top-1/2 left-0 right-0 h-px bg-border" />
        </div>

        {/* quadrant labels */}
        <span className="absolute top-2 left-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/80">
          Auth · Left
        </span>
        <span className="absolute top-2 right-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/80">
          Auth · Right
        </span>
        <span className="absolute bottom-2 left-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/80">
          Lib · Left
        </span>
        <span className="absolute bottom-2 right-2 text-[10px] uppercase tracking-wider font-semibold text-muted-foreground/80">
          Lib · Right
        </span>

        {/* axis end labels */}
        <span className="absolute -top-5 left-1/2 -translate-x-1/2 text-[10px] uppercase tracking-wider text-muted-foreground">
          Authoritarian
        </span>
        <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[10px] uppercase tracking-wider text-muted-foreground">
          Libertarian
        </span>
        <span className="absolute top-1/2 -translate-y-1/2 -left-12 text-[10px] uppercase tracking-wider text-muted-foreground rotate-0">
          Left
        </span>
        <span className="absolute top-1/2 -translate-y-1/2 -right-9 text-[10px] uppercase tracking-wider text-muted-foreground">
          Right
        </span>

        {/* anchor marker — only shown when a non-global view is active */}
        {isAnchored && viewAnchor && (
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 grid h-6 w-6 place-items-center rounded-full border-2 border-dashed border-accent bg-background text-[10px] cursor-default"
                aria-label={`Anchor: ${viewAnchor.name}`}
              >
                {viewAnchor.flag}
              </span>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-[240px]">
              <div className="font-semibold">{viewAnchor.name}</div>
              <p className="text-xs text-muted-foreground mt-0.5 leading-snug">
                {viewAnchor.description}
              </p>
            </TooltipContent>
          </Tooltip>
        )}

        {/* dots — positioned in the viewed (anchor-adjusted) frame */}
        {points.map((p) => {
          const x = toPercent(p.viewedEconomic);
          // social axis: -1 (authoritarian) → top of chart, +1 (libertarian) → bottom
          const y = toPercent(p.viewedSocial);
          return (
            <Tooltip key={p.id}>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  className="absolute -translate-x-1/2 -translate-y-1/2 group focus:outline-none"
                  style={{ left: `${x}%`, top: `${y}%` }}
                  aria-label={`${p.sourceName}: ${p.label}`}
                >
                  <span
                    className={cn(
                      "block h-3 w-3 rounded-full ring-2 ring-background shadow transition-transform group-hover:scale-150 group-focus-visible:scale-150",
                      dotColor(p.direction)
                    )}
                  />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-[260px]">
                <div className="space-y-1.5">
                  <div className="font-semibold flex items-center gap-1.5">
                    <span aria-hidden="true">{countryFlag(p.country)}</span>
                    {p.sourceName}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {p.label} · econ {p.economic > 0 ? "+" : ""}
                    {p.economic.toFixed(2)} · social {p.social > 0 ? "+" : ""}
                    {p.social.toFixed(2)}
                  </div>
                  {isAnchored && viewAnchor && (
                    <div className="text-xs text-accent">
                      Through {viewAnchor.short_name}: econ{" "}
                      {p.viewedEconomic > 0 ? "+" : ""}
                      {p.viewedEconomic.toFixed(2)} · social{" "}
                      {p.viewedSocial > 0 ? "+" : ""}
                      {p.viewedSocial.toFixed(2)}
                    </div>
                  )}
                  {p.regional && (
                    <p className="text-xs leading-snug text-foreground/80">
                      {p.regional}
                    </p>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>

      <aside className="space-y-2 text-xs md:max-w-[220px]">
        {isAnchored && viewAnchor ? (
          <p className="text-muted-foreground leading-relaxed">
            Viewed from the{" "}
            <span className="text-foreground font-medium">
              {viewAnchor.name}
            </span>
            . The centre marks where this region's median sits; dots show how
            each source falls{" "}
            <em className="text-foreground/90">relative to that baseline</em>.
          </p>
        ) : (
          <p className="text-muted-foreground leading-relaxed">
            Each dot is one source, placed by the analyzer along an{" "}
            <span className="text-foreground font-medium">economic</span> (left ↔
            right) and{" "}
            <span className="text-foreground font-medium">social</span>{" "}
            (authoritarian ↔ libertarian) axis. Pick a region above to
            re-anchor the view.
          </p>
        )}
        <ul className="space-y-1 pt-2">
          {points.map((p) => {
            const econ = isAnchored ? p.viewedEconomic : p.economic;
            const social = isAnchored ? p.viewedSocial : p.social;
            return (
              <li
                key={`${p.id}-legend`}
                className="flex items-center gap-2 truncate"
              >
                <span
                  className={cn(
                    "h-2 w-2 rounded-full shrink-0",
                    dotColor(p.direction)
                  )}
                />
                <span className="truncate text-foreground/90">
                  {p.sourceName}
                </span>
                <span className="text-muted-foreground ml-auto shrink-0 tabular-nums">
                  {econ > 0 ? "+" : ""}
                  {econ.toFixed(1)},{" "}
                  {social > 0 ? "+" : ""}
                  {social.toFixed(1)}
                </span>
              </li>
            );
          })}
        </ul>
      </aside>
    </div>
  );
}
