from __future__ import annotations

from app.models.article import Article


async def extract_and_dedupe(articles: list[Article]) -> list[Article]:
    """Extract full article text and remove near-duplicate articles.

    For each article whose full_text is a stub or snippet, fetches the full
    page and extracts clean body text using trafilatura (preferred) or
    newspaper3k. Then runs cosine-similarity deduplication on text embeddings
    (TF-IDF or OpenAI text-embedding-3-small) and drops articles with pairwise
    similarity above 0.85 — keeping the version from the more credible source.

    Args:
        articles: Raw articles from all searchers (may have partial text).

    Returns:
        Deduplicated list with full_text populated on each Article.
    """
    # TODO(THE-9): implement trafilatura/newspaper3k full-text extraction;
    #              implement embedding-based deduplication (cosine similarity > 0.85);
    #              remember to uncomment trafilatura/newspaper3k in pyproject.toml
    return articles
