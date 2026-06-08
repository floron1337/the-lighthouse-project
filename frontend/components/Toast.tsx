"use client";

import * as React from "react";
import { Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ToastProps {
  open: boolean;
  title: string;
  description?: string;
  /** Auto-dismiss after this many ms; pass 0 to disable. */
  durationMs?: number;
  onDismiss: () => void;
  /** Tone changes the accent color. */
  tone?: "info" | "warning";
}

export function Toast({
  open,
  title,
  description,
  durationMs = 5000,
  onDismiss,
  tone = "info",
}: ToastProps) {
  const [mounted, setMounted] = React.useState(open);
  const [visible, setVisible] = React.useState(false);

  // Mount/unmount sequence: when `open` flips to true we mount immediately
  // and fade in next frame; when it flips to false we fade out first,
  // then unmount after the transition completes.
  React.useEffect(() => {
    if (open) {
      setMounted(true);
      const id = requestAnimationFrame(() => setVisible(true));
      return () => cancelAnimationFrame(id);
    }
    setVisible(false);
    const id = setTimeout(() => setMounted(false), 350);
    return () => clearTimeout(id);
  }, [open]);

  // Auto-dismiss
  React.useEffect(() => {
    if (!open || durationMs <= 0) return;
    const id = setTimeout(onDismiss, durationMs);
    return () => clearTimeout(id);
  }, [open, durationMs, onDismiss]);

  if (!mounted) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed bottom-6 right-6 z-50 max-w-sm w-[min(380px,calc(100vw-3rem))]"
    >
      <div
        className={cn(
          "pointer-events-auto rounded-xl border bg-card shadow-lg px-4 py-3",
          "transition-all duration-300 ease-out",
          visible
            ? "opacity-100 translate-y-0"
            : "opacity-0 translate-y-2",
          tone === "warning" && "border-bias-mixed/40"
        )}
      >
        <div className="flex items-start gap-3">
          <Info
            className={cn(
              "h-4 w-4 mt-0.5 shrink-0",
              tone === "warning" ? "text-bias-mixed" : "text-accent"
            )}
            aria-hidden="true"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-foreground leading-tight">
              {title}
            </p>
            {description && (
              <p
                className={cn(
                  "mt-1 text-xs text-muted-foreground leading-relaxed",
                  "transition-opacity duration-1000",
                  visible ? "opacity-100" : "opacity-0"
                )}
              >
                {description}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onDismiss}
            aria-label="Dismiss notification"
            className="text-muted-foreground/60 hover:text-foreground transition-colors -mt-0.5"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
        {durationMs > 0 && (
          <span
            aria-hidden="true"
            className="mt-2 block h-0.5 rounded-full bg-accent/60 origin-left"
            style={{
              animation: visible
                ? `lighthouse-toast-bar ${durationMs}ms linear forwards`
                : "none",
            }}
          />
        )}
      </div>
      <style jsx>{`
        @keyframes lighthouse-toast-bar {
          from { transform: scaleX(1); }
          to { transform: scaleX(0); }
        }
      `}</style>
    </div>
  );
}
