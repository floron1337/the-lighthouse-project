"use client";

import { FormEvent, useState } from "react";

interface SearchBarProps {
  onSearch: (query: string) => void;
  disabled?: boolean;
}

export default function SearchBar({
  onSearch,
  disabled = false,
}: SearchBarProps) {
  const [value, setValue] = useState("");

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (trimmed) onSearch(trimmed);
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 w-full max-w-2xl">
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="e.g. EU AI Act, South China Sea, Ukraine ceasefire…"
        disabled={disabled}
        aria-label="News topic"
        className="flex-1 rounded-xl border border-gray-300 bg-white px-5 py-3 text-base
                   shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500
                   disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="rounded-xl bg-blue-600 px-6 py-3 text-white font-semibold
                   hover:bg-blue-700 active:bg-blue-800
                   disabled:opacity-50 disabled:cursor-not-allowed
                   transition-colors"
      >
        Search
      </button>
    </form>
  );
}
