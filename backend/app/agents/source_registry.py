from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def load_registry() -> list[dict]:
    """Load the curated source registry from source_registry.json.

    Cached after the first call to avoid repeated disk reads during a request.
    Returns a list of source metadata dicts.
    """
    path = Path(__file__).parent.parent / "source_registry.json"
    with open(path) as f:
        return json.load(f)


def get_source(source_id: str, registry: list[dict] | None = None) -> dict | None:
    """Look up a source entry by its id. Returns None if not found."""
    if registry is None:
        registry = load_registry()
    return next((s for s in registry if s["id"] == source_id), None)


_SOURCE_ALIASES: dict[str, str] = {
    "abc news au": "ABC Australia",
    "al jazeera english": "Al Jazeera",
    "associated press": "AP News",
    "dw": "Deutsche Welle",
    "dw english": "Deutsche Welle",
    "the times of india": "Times of India",
}


def _normalise_source_name(name: str) -> str:
    name = name.casefold()
    name = name.replace("&", " and ")
    name = re.sub(r"\([^)]*\)", " ", name)
    name = re.sub(r"[^a-z0-9]+", " ", name)
    words = [
        word
        for word in name.split()
        if word not in {"news", "english", "online", "www"}
    ]
    return " ".join(words)


def _slugify_source_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")
    return slug or "unknown_source"


def resolve_source_name(
    name: str,
    country: str = "",
    registry: list[dict] | None = None,
) -> tuple[str, str]:
    """Map an API source name to a registry id/country pair.

    Avoids unsafe substring matches for very short source names like "RT",
    which otherwise match unrelated outlets such as "Fortune".
    """
    if registry is None:
        registry = load_registry()

    raw_name = (name or "Unknown").strip()
    aliased = _SOURCE_ALIASES.get(_normalise_source_name(raw_name))
    lookup_name = aliased or raw_name
    normalised = _normalise_source_name(lookup_name)

    registry_names = [
        (entry, _normalise_source_name(str(entry.get("name", ""))))
        for entry in registry
    ]

    for entry, entry_name in registry_names:
        if normalised and normalised == entry_name:
            return str(entry["id"]), str(entry["country"])

    source_tokens = set(normalised.split())
    best_entry: dict | None = None
    best_score = 0.0
    for entry, entry_name in registry_names:
        entry_tokens = set(entry_name.split())
        if not source_tokens or not entry_tokens:
            continue
        if len(source_tokens) == 1 or len(entry_tokens) == 1:
            continue
        overlap = source_tokens & entry_tokens
        score = len(overlap) / max(len(source_tokens | entry_tokens), 1)
        if score >= 0.67 and score > best_score:
            best_entry = entry
            best_score = score

    if best_entry is not None:
        return str(best_entry["id"]), str(best_entry["country"])

    return _slugify_source_name(raw_name), country or "XX"
