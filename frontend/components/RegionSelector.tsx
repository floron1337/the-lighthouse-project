"use client";

import { RegionalAnchor } from "@/lib/streamClient";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface RegionSelectorProps {
  anchors: RegionalAnchor[];
  selectedId: string;
  onChange: (anchorId: string) => void;
}

export function RegionSelector({
  anchors,
  selectedId,
  onChange,
}: RegionSelectorProps) {
  if (anchors.length === 0) return null;

  return (
    <div
      role="radiogroup"
      aria-label="View political compass through which median citizen"
      className="flex flex-wrap items-center gap-1.5"
    >
      <span className="text-xs uppercase tracking-wider text-muted-foreground mr-1">
        Viewed from
      </span>
      {anchors.map((anchor) => {
        const isActive = anchor.id === selectedId;
        return (
          <Tooltip key={anchor.id}>
            <TooltipTrigger asChild>
              <button
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => onChange(anchor.id)}
                className={cn(
                  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
                  "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
                  isActive
                    ? "border-accent bg-accent text-accent-foreground shadow-sm"
                    : "border-border bg-background/60 text-muted-foreground hover:text-foreground hover:border-accent/60 hover:bg-accent/5"
                )}
              >
                <span aria-hidden="true">{anchor.flag}</span>
                {anchor.short_name}
              </button>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-[240px]">
              <div className="font-semibold">{anchor.name}</div>
              <p className="text-xs text-muted-foreground mt-0.5 leading-snug">
                {anchor.description}
              </p>
              {anchor.id !== "global" && (
                <p className="text-[10px] text-muted-foreground/80 mt-1 tabular-nums">
                  anchor: econ {anchor.economic_axis > 0 ? "+" : ""}
                  {anchor.economic_axis.toFixed(2)}, social{" "}
                  {anchor.social_axis > 0 ? "+" : ""}
                  {anchor.social_axis.toFixed(2)}
                </p>
              )}
            </TooltipContent>
          </Tooltip>
        );
      })}
    </div>
  );
}
