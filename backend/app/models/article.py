from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Article(BaseModel):
    title: str
    full_text: str
    url: str
    source_id: str          # maps to an entry in source_registry.json
    source_name: str
    country: str            # ISO 3166-1 alpha-2
    published_at: datetime
    author: Optional[str] = None
    language: str = "en"   # BCP 47 language tag of the original article
    translated_text: Optional[str] = None  # English translation if language != "en"


class ArticleBundle(BaseModel):
    query: str
    articles: list[Article]
    sources_covered: list[str]
    countries_covered: list[str]
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow)
