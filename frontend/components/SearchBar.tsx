"use client";

import { FormEvent, useState } from "react";
import { Search, Loader2, ArrowRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  onSearch: (query: string) => void;
  disabled?: boolean;
}

const SUGGESTIONS = [
  "EU AI Act",
  "South China Sea tensions",
  "Ukraine ceasefire talks",
  "BRICS summit 2026",
];

export default function SearchBar({
  onSearch,
  disabled = false,
}: SearchBarProps) {
  const [value, setValue] = useState("");

  function submit(query: string) {
    const trimmed = query.trim();
    if (!trimmed) return;
    onSearch(trimmed);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    submit(value);
  }

  return (
    <div className="w-full max-w-3xl flex flex-col gap-4">
      <form
        onSubmit={handleSubmit}
        className={cn(
          "relative flex items-center gap-2 rounded-2xl border bg-card p-2 shadow-sm",
          "focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background",
          "transition-all"
        )}
      >
        <Search
          className="ml-3 h-5 w-5 text-muted-foreground shrink-0"
          aria-hidden="true"
        />
        <Input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Search a topic — e.g. EU AI Act"
          disabled={disabled}
          aria-label="News topic"
          className="border-0 bg-transparent shadow-none focus-visible:ring-0 focus-visible:ring-offset-0 text-base h-11 px-1"
        />
        <Button
          type="submit"
          variant="default"
          disabled={disabled || !value.trim()}
          className="h-11 rounded-xl px-5"
        >
          {disabled ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="hidden sm:inline">Crawling…</span>
            </>
          ) : (
            <>
              <span className="hidden sm:inline">Analyze</span>
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </Button>
      </form>

      <div className="flex flex-wrap items-center gap-2 px-1">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">
          Try
        </span>
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            disabled={disabled}
            onClick={() => {
              setValue(s);
              submit(s);
            }}
            className={cn(
              "text-xs rounded-full border border-border bg-background/60 px-3 py-1",
              "text-muted-foreground hover:text-foreground hover:border-accent/60 hover:bg-accent/5",
              "transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            )}
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
