"""Curated RSS feeds for tech / science / robotics news."""

from __future__ import annotations

from typing import Any

import feedparser

from content_factory.utils.logging import get_logger

log = get_logger(__name__)

DEFAULT_FEEDS: list[tuple[str, str]] = [
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("The Verge", "https://www.theverge.com/rss/index.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ("Google AI Blog", "https://blog.google/technology/ai/rss/"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("IEEE Spectrum", "https://spectrum.ieee.org/feeds/feed.rss"),
    ("Nature News", "https://www.nature.com/nature.rss"),
    ("NASA", "https://www.nasa.gov/rss/dyn/breaking_news.rss"),
]


def fetch_recent_headlines(
    feeds: list[tuple[str, str]] | None = None,
    *,
    per_feed: int = 5,
) -> list[dict[str, Any]]:
    feeds = feeds or DEFAULT_FEEDS
    items: list[dict[str, Any]] = []
    for publisher, url in feeds:
        try:
            parsed = feedparser.parse(url)
            for entry in parsed.entries[:per_feed]:
                items.append(
                    {
                        "title": getattr(entry, "title", "") or "",
                        "url": getattr(entry, "link", "") or "",
                        "snippet": getattr(entry, "summary", "")[:400]
                        if hasattr(entry, "summary")
                        else "",
                        "publisher": publisher,
                        "published_at": getattr(entry, "published", "") or "",
                        "source": "rss",
                    }
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("RSS fetch failed for %s: %s", publisher, exc)
    return items
