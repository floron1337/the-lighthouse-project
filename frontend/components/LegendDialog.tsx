"use client";

import * as React from "react";
import { BookOpen, Compass } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

interface BiasItem {
  variant: "west" | "brics" | "neutral" | "government" | "mixed";
  label: string;
  description: string;
}

const BIAS_DIRECTIONS: BiasItem[] = [
  {
    variant: "west",
    label: "pro-Western",
    description:
      "Aligned with NATO / Five Eyes framing — emphasizes Western-aligned actors as the lawful/legitimate side of a dispute.",
  },
  {
    variant: "brics",
    label: "pro-BRICS",
    description:
      "Aligned with BRICS+ framing — centers Russian, Chinese, Indian, or other BRICS perspectives as the legitimate viewpoint.",
  },
  {
    variant: "government",
    label: "pro-government",
    description:
      "Centers the domestic government's view — often the case with state-funded outlets reporting on their own state.",
  },
  {
    variant: "neutral",
    label: "neutral",
    description:
      "Reports the story without obvious framing slant — uses balanced attribution and avoids loaded language.",
  },
  {
    variant: "mixed",
    label: "mixed",
    description:
      "The framing crosses categories — for example, geopolitically Western but with domestic-government slant on a specific issue.",
  },
];

interface SentimentItem {
  label: string;
  range: string;
  dot: string;
  text: string;
}

const SENTIMENT_BANDS: SentimentItem[] = [
  {
    label: "Positive",
    range: "score > +0.25",
    dot: "bg-bias-neutral",
    text: "text-bias-neutral",
  },
  {
    label: "Neutral",
    range: "−0.25 ≤ score ≤ +0.25",
    dot: "bg-muted-foreground",
    text: "text-muted-foreground",
  },
  {
    label: "Negative",
    range: "score < −0.25",
    dot: "bg-bias-brics",
    text: "text-bias-brics",
  },
];

export function LegendDialog() {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <BookOpen className="h-3.5 w-3.5" />
          Legend
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>What the indicators mean</DialogTitle>
          <DialogDescription>
            Every article card shows several at-a-glance signals from the
            bias-analysis agent. Here is what each one is measuring.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6 text-sm">
          <Section title="Bias direction">
            <p className="text-muted-foreground">
              The colored pill names the inferred geopolitical alignment of
              the source's framing for this specific story.
            </p>
            <ul className="mt-3 space-y-2.5">
              {BIAS_DIRECTIONS.map((d) => (
                <li key={d.variant} className="flex items-start gap-3">
                  <Badge variant={d.variant} className="shrink-0">
                    {d.label}
                  </Badge>
                  <p className="text-foreground/85 leading-snug">
                    {d.description}
                  </p>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Confidence">
            <div className="flex items-center gap-3">
              <span className="w-16 shrink-0">
                <Progress
                  value={80}
                  className="h-1.5"
                  indicatorClassName="bg-accent"
                />
              </span>
              <span className="text-xs text-muted-foreground tabular-nums">
                80%
              </span>
            </div>
            <p className="text-muted-foreground mt-2">
              How sure the analyzer is in the assignment. Below ~50% the
              direction is essentially a guess; above 80% the framing is
              clearly recognizable in the article text.
            </p>
          </Section>

          <Section title="Sentiment">
            <p className="text-muted-foreground">
              Emotional valence of the article's language, scored from −1
              (highly negative) to +1 (highly positive).
            </p>
            <ul className="mt-3 grid sm:grid-cols-3 gap-2">
              {SENTIMENT_BANDS.map((s) => (
                <li
                  key={s.label}
                  className="rounded-lg border bg-card/60 px-3 py-2"
                >
                  <span className={cn("flex items-center gap-1.5 text-xs font-medium", s.text)}>
                    <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} />
                    {s.label}
                  </span>
                  <span className="block text-[10px] text-muted-foreground mt-0.5 tabular-nums">
                    {s.range}
                  </span>
                </li>
              ))}
            </ul>
          </Section>

          <Section title="Mini political compass">
            <div className="flex items-start gap-3">
              <span
                className="relative inline-block rounded-md border bg-card overflow-hidden shrink-0"
                style={{ width: 40, height: 40 }}
              >
                <span className="absolute left-1/2 top-0 bottom-0 w-px bg-border" />
                <span className="absolute top-1/2 left-0 right-0 h-px bg-border" />
                <span
                  className="absolute h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-bias-west ring-1 ring-background"
                  style={{ left: "70%", top: "30%" }}
                />
              </span>
              <p className="text-muted-foreground leading-relaxed">
                Plots the source on an{" "}
                <span className="text-foreground font-medium">economic</span>{" "}
                axis (left ↔ right) and a{" "}
                <span className="text-foreground font-medium">social</span>{" "}
                axis (authoritarian top ↔ libertarian bottom). The big
                compass in the <em>Spectrum</em> tab lets you re-anchor the
                view to a specific region's median citizen.
              </p>
            </div>
          </Section>

          <Section title="Loaded terms">
            <div className="flex flex-wrap gap-1.5">
              <span className="text-xs px-2 py-0.5 rounded-md bg-bias-mixed/15 text-bias-mixed font-medium">
                regime
              </span>
              <span className="text-xs px-2 py-0.5 rounded-md bg-bias-mixed/15 text-bias-mixed font-medium">
                freedom fighters
              </span>
              <span className="text-xs px-2 py-0.5 rounded-md bg-bias-mixed/15 text-bias-mixed font-medium">
                wider conflict
              </span>
            </div>
            <p className="text-muted-foreground mt-2">
              Politically charged word choices the analyzer flagged in the
              article text. Same event reported by another outlet might use
              neutral synonyms (<em>government</em>, <em>militants</em>,{" "}
              <em>tensions</em>).
            </p>
          </Section>

          <Section title="Possible omissions">
            <p className="text-muted-foreground">
              Topics or perspectives other sources on the same story covered
              but this one did not. Computed by comparing the article's
              extracted points against the cross-source consensus — useful
              for spotting framing-by-exclusion.
            </p>
          </Section>

          <Section title="Region perspective">
            <div className="flex items-start gap-3">
              <span className="grid h-7 w-7 place-items-center rounded-full border-2 border-dashed border-accent bg-background text-sm shrink-0">
                <Compass className="h-3.5 w-3.5 text-accent" />
              </span>
              <p className="text-muted-foreground leading-relaxed">
                On the big compass, the “Viewed from" chips re-anchor every
                dot to a region's median citizen. The dashed flag marker
                shows where the chosen baseline sits. Useful for testing
                how the same outlet reads as <em>centre-right</em> by US
                standards but <em>right</em> by EU standards.
              </p>
            </div>
          </Section>
        </div>

        <p className="text-[11px] text-muted-foreground border-t pt-3">
          The analyzer combines deterministic cross-source comparison with
          an LLM. All scores are estimates — treat them as a reading aid,
          not a verdict.
        </p>
      </DialogContent>
    </Dialog>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h3 className="text-xs uppercase tracking-wider font-semibold text-foreground border-b pb-1.5 mb-3">
        {title}
      </h3>
      {children}
    </section>
  );
}
