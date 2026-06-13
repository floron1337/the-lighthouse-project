"use client";

import * as React from "react";
import {
  ComposableMap,
  Geographies,
  Geography,
} from "react-simple-maps";
import { iso2ToNumeric } from "@/lib/iso";
import { Article } from "@/lib/streamClient";
import { countryFlag } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const GEO_URL =
  "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

interface RegionMapProps {
  articles: Article[];
  selectedCountry?: string | null;
  onCountryClick?: (iso2: string | null) => void;
}

export default function RegionMap({ articles, selectedCountry, onCountryClick }: RegionMapProps) {
  const counts = React.useMemo(() => {
    const m = new Map<string, { count: number; sources: Set<string>; iso2: string }>();
    for (const a of articles) {
      const id = iso2ToNumeric(a.country);
      if (!id) continue;
      const existing = m.get(id) ?? { count: 0, sources: new Set<string>(), iso2: a.country.toUpperCase() };
      existing.count += 1;
      existing.sources.add(a.source_name);
      m.set(id, existing);
    }
    return m;
  }, [articles]);

  const maxCount = Math.max(1, ...Array.from(counts.values()).map((v) => v.count));
  const totalCountries = counts.size;

  return (
    <div className="rounded-xl border bg-card overflow-hidden">
      <div className="flex items-center justify-between gap-3 px-5 py-3 border-b">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider">
            Regional coverage
          </h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Countries highlighted by source origin · darker = more sources
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="inline-flex h-6 items-center rounded-full bg-accent/15 px-2.5 font-medium text-accent">
            {totalCountries} {totalCountries === 1 ? "country" : "countries"}
          </span>
        </div>
      </div>

      <div className="p-2 sm:p-4 bg-gradient-to-b from-muted/40 to-background">
        <ComposableMap
          projection="geoEqualEarth"
          projectionConfig={{ scale: 155 }}
          width={900}
          height={420}
          style={{ width: "100%", height: "auto" }}
        >
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map((geo) => {
                const id = String(geo.id).padStart(3, "0");
                const data = counts.get(id);
                const sourceData =
                  data && data.sources.size > 0 ? data : null;
                const hasSources = sourceData != null;
                const countryName = geo.properties?.name ?? "Country";
                const isSelected =
                  sourceData != null && selectedCountry === sourceData.iso2;
                const isDimmed = selectedCountry != null && !isSelected;
                const intensity = data ? data.count / maxCount : 0;
                const fill = isSelected
                  ? "hsl(var(--accent))"
                  : data
                  ? `hsl(var(--accent) / ${isDimmed ? 0.2 : 0.45 + intensity * 0.5})`
                  : `hsl(var(--muted-foreground) / ${isDimmed ? 0.08 : 0.18})`;
                const stroke = isSelected
                  ? "hsl(var(--accent))"
                  : data
                  ? `hsl(var(--accent) / ${isDimmed ? 0.3 : 1})`
                  : "hsl(var(--muted-foreground) / 0.45)";

                const geography = (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    aria-label={
                      sourceData
                        ? `${countryName}: ${sourceData.count} article${
                            sourceData.count !== 1 ? "s" : ""
                          }`
                        : `${countryName}: no news sources`
                    }
                    aria-disabled={!hasSources}
                    data-has-news-sources={hasSources}
                    onClick={
                      sourceData && onCountryClick
                        ? () => {
                            onCountryClick(
                              isSelected ? null : sourceData.iso2
                            );
                          }
                        : undefined
                    }
                    style={{
                      default: {
                        fill,
                        stroke,
                        strokeWidth: isSelected ? 1 : data ? 0.75 : 0.5,
                        outline: "none",
                        transition: "fill 150ms ease",
                      },
                      hover: {
                        fill: data
                          ? "hsl(var(--accent))"
                          : "hsl(var(--muted-foreground) / 0.35)",
                        stroke: "hsl(var(--accent))",
                        strokeWidth: 0.9,
                        outline: "none",
                        cursor: hasSources ? "pointer" : "default",
                      },
                      pressed: {
                        fill: hasSources
                          ? "hsl(var(--accent))"
                          : "hsl(var(--muted-foreground) / 0.35)",
                        outline: "none",
                      },
                    }}
                  />
                );

                return (
                  <Tooltip key={geo.rsmKey}>
                    <TooltipTrigger asChild>{geography}</TooltipTrigger>
                    <TooltipContent side="top">
                      <div className="space-y-1">
                        <div className="font-semibold flex items-center gap-1.5">
                          {countryName}
                        </div>
                        {sourceData ? (
                          <div className="text-xs text-muted-foreground">
                            {sourceData.count} article
                            {sourceData.count !== 1 ? "s" : ""} ·{" "}
                            {Array.from(sourceData.sources).join(", ")}
                          </div>
                        ) : (
                          <div className="text-xs text-muted-foreground">
                            No news sources for this query
                          </div>
                        )}
                      </div>
                    </TooltipContent>
                  </Tooltip>
                );
              })
            }
          </Geographies>
        </ComposableMap>
      </div>

      {totalCountries > 0 && (
        <div className="flex flex-wrap gap-1.5 px-5 pb-4 pt-1 text-xs text-muted-foreground border-t">
          <span className="mr-1 uppercase tracking-wider">Covered:</span>
          {Array.from(counts.entries()).map(([id, d]) => {
            const article = articles.find(
              (a) => iso2ToNumeric(a.country) === id
            );
            const code = article?.country ?? "";
            return (
              <span
                key={id}
                className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-0.5"
              >
                <span aria-hidden="true">{countryFlag(code)}</span>
                <span className="text-foreground/80">{code}</span>
                <span className="text-muted-foreground">· {d.count}</span>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
