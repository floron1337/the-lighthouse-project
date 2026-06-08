"use client";

import { PoliticalCompassPoint } from "@/lib/streamClient";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface MiniCompassProps {
  compass: PoliticalCompassPoint;
  /** Tailwind bg-* class for the dot (matches the source's bias direction) */
  dotClassName?: string;
  size?: number;
}

function toPercent(value: number): number {
  const clamped = Math.max(-1, Math.min(1, value));
  return ((clamped + 1) / 2) * 100;
}

export function MiniCompass({
  compass,
  dotClassName = "bg-accent",
  size = 32,
}: MiniCompassProps) {
  const x = toPercent(compass.economic_axis);
  const y = 100 - toPercent(compass.social_axis);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className="relative inline-block rounded-md border bg-card overflow-hidden shrink-0"
          style={{ width: size, height: size }}
          aria-label={`Political compass: ${compass.label}`}
        >
          <span className="absolute left-1/2 top-0 bottom-0 w-px bg-border" />
          <span className="absolute top-1/2 left-0 right-0 h-px bg-border" />
          <span
            className={cn(
              "absolute h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-1 ring-background",
              dotClassName
            )}
            style={{ left: `${x}%`, top: `${y}%` }}
          />
        </span>
      </TooltipTrigger>
      <TooltipContent side="top" className="text-xs max-w-[220px]">
        <div className="font-semibold">{compass.label}</div>
        <div className="text-muted-foreground">
          econ {compass.economic_axis > 0 ? "+" : ""}
          {compass.economic_axis.toFixed(2)} · social{" "}
          {compass.social_axis > 0 ? "+" : ""}
          {compass.social_axis.toFixed(2)}
        </div>
        {compass.regional_context && (
          <p className="mt-1 leading-snug text-foreground/80">
            {compass.regional_context}
          </p>
        )}
      </TooltipContent>
    </Tooltip>
  );
}
