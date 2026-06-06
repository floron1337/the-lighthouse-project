from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

import httpx

from app.agents.source_registry import load_registry
from app.models.article import Article

logger = logging.getLogger(__name__)

_MIN_TEXT_LEN = 200
_DEDUP_THRESHOLD = 0.85


@lru_cache(maxsize=1)
def _registry_credibility() -> dict[str, float]:
    return {s["id"]: s.get("credibility_score", 0.5) for s in load_registry()}


async def _fetch_full_text(url: str) -> str | None:
    """Fetch a URL and extract clean article body text via trafilatura."""
    try:
        import trafilatura  # noqa: PLC0415

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; LighthouseBot/1.0)"})
            resp.raise_for_status()
            text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
            return text or None
    except Exception as exc:
        logger.debug("Text extraction failed for %s: %s", url, exc)
        return None


def _tfidf_similarity(texts: list[str]) -> list[list[float]]:
    """Return an n×n cosine-similarity matrix using TF-IDF vectors."""
    from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: PLC0415
    from sklearn.metrics.pairwise import cosine_similarity  # noqa: PLC0415

    vec = TfidfVectorizer(max_features=5000, sublinear_tf=True)
    matrix = vec.fit_transform(texts)
    sim = cosine_similarity(matrix)
    return sim.tolist()


async def extract_and_dedupe(articles: list[Article]) -> list[Article]:
    """Extract full article text and remove near-duplicate articles.

    For each article whose full_text is a stub or snippet, fetches the full
    page and extracts clean body text using trafilatura. Then runs cosine-
    similarity deduplication on TF-IDF vectors and drops articles with
    pairwise similarity above 0.85 — keeping the version from the more
    credible source.

    Args:
        articles: Raw articles from all searchers (may have partial text).

    Returns:
        Deduplicated list with full_text populated on each Article.
    """
    if not articles:
        return articles

    # --- 1. Full-text extraction --------------------------------------------------
    async def enrich(article: Article) -> Article:
        if len(article.full_text) < _MIN_TEXT_LEN and article.url.startswith("http"):
            fetched = await _fetch_full_text(article.url)
            if fetched:
                return article.model_copy(update={"full_text": fetched})
        return article

    enriched: list[Article] = await asyncio.gather(*[enrich(a) for a in articles])

    # --- 2. TF-IDF deduplication -------------------------------------------------
    try:
        texts = [a.full_text or a.title for a in enriched]
        sim = _tfidf_similarity(texts)
    except Exception as exc:
        logger.warning("TF-IDF dedup skipped: %s", exc)
        return enriched

    credibility = _registry_credibility()
    n = len(enriched)
    dropped: set[int] = set()

    for i in range(n):
        if i in dropped:
            continue
        for j in range(i + 1, n):
            if j in dropped:
                continue
            if sim[i][j] >= _DEDUP_THRESHOLD:
                cred_i = credibility.get(enriched[i].source_id, 0.5)
                cred_j = credibility.get(enriched[j].source_id, 0.5)
                # Keep the article from the more credible source
                dropped.add(j if cred_i >= cred_j else i)

    return [a for idx, a in enumerate(enriched) if idx not in dropped]
