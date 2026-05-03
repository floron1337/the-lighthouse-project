from __future__ import annotations

import json
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
