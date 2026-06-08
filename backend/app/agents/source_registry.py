from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from app.agents.searchers._source_map import country_for_name

if TYPE_CHECKING:
    from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


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
_LLM_COUNTRY_CACHE: dict[tuple[str, str], str] = {}
_LLM_COUNTRY_CONFIDENCE_THRESHOLD = 0.75
_INVALID_COUNTRY_CODES = {"EU", "UK", "UN", "XX"}

_COUNTRY_NAME_TO_ISO2: dict[str, str] = {
    "australia": "AU",
    "canada": "CA",
    "france": "FR",
    "germany": "DE",
    "india": "IN",
    "ireland": "IE",
    "japan": "JP",
    "nigeria": "NG",
    "qatar": "QA",
    "singapore": "SG",
    "south africa": "ZA",
    "united kingdom": "GB",
    "uk": "GB",
    "united states": "US",
    "usa": "US",
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


def _normalise_llm_country(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    by_name = _COUNTRY_NAME_TO_ISO2.get(cleaned.casefold())
    if by_name:
        return by_name
    code = cleaned.upper()
    if code == "UK":
        return "GB"
    if re.fullmatch(r"[A-Z]{2}", code) and code not in _INVALID_COUNTRY_CODES:
        return code
    return None


def _source_domain(url: str) -> str:
    host = urlparse(url).netloc.casefold()
    return host.removeprefix("www.")


def _llm_country_prompt(source_name: str, url: str = "", title: str = "") -> str:
    domain = _source_domain(url)
    return f"""\
You identify the country of origin of news outlets for source metadata.

Source name: {source_name or "Unknown"}
Article domain: {domain or "unknown"}
Article title: {title[:240] or "unknown"}

Return ONLY JSON with:
{{
  "country_code": "ISO 3166-1 alpha-2 code, or XX if uncertain",
  "confidence": 0.0,
  "reason": "brief reason"
}}

Rules:
- Identify the outlet/source country, not the article's subject country.
- Use "GB" for the United Kingdom.
- Use "XX" unless you are confident.
"""


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

    resolved_country = _normalise_llm_country(country) or country_for_name(raw_name) or "XX"
    return _slugify_source_name(raw_name), resolved_country


async def resolve_source_name_with_llm(
    name: str,
    country: str = "",
    registry: list[dict] | None = None,
    llm_service: "LLMService | None" = None,
    *,
    url: str = "",
    title: str = "",
) -> tuple[str, str]:
    """Resolve a source, using the LLM only as a high-confidence country fallback."""
    source_id, resolved_country = resolve_source_name(name, country, registry)
    if resolved_country != "XX":
        return source_id, resolved_country
    if llm_service is None or getattr(llm_service, "use_mock", False):
        return source_id, resolved_country

    raw_name = (name or "Unknown").strip()
    domain = _source_domain(url)
    deterministic_country = country_for_name(f"{raw_name} {domain}")
    if deterministic_country:
        return source_id, deterministic_country

    cache_key = (_normalise_source_name(raw_name), domain)
    if cache_key in _LLM_COUNTRY_CACHE:
        return source_id, _LLM_COUNTRY_CACHE[cache_key]

    try:
        raw = await llm_service.complete(
            _llm_country_prompt(raw_name, url=url, title=title),
            json_mode=True,
        )
        cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(cleaned)
        country_code = _normalise_llm_country(data.get("country_code") or data.get("country"))
        confidence = float(data.get("confidence", 0.0))
    except Exception as exc:
        logger.debug("LLM source-country resolution failed for %r: %s", raw_name, exc)
        return source_id, resolved_country

    if country_code is None or confidence < _LLM_COUNTRY_CONFIDENCE_THRESHOLD:
        return source_id, resolved_country

    _LLM_COUNTRY_CACHE[cache_key] = country_code
    return source_id, country_code
