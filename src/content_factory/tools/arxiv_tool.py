"""arXiv paper search."""

from __future__ import annotations

from typing import Any

from content_factory.utils.logging import get_logger

log = get_logger(__name__)


def search_arxiv(
    query: str,
    *,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Search arXiv and return compact paper dicts."""
    try:
        import arxiv
    except ImportError:
        log.warning("arxiv package not installed")
        return []

    # page_size must stay small — default 100 is slow and rate-limit prone
    client = arxiv.Client(page_size=max(1, min(max_results, 10)), delay_seconds=1.0)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )
    results: list[dict[str, Any]] = []
    try:
        for i, paper in enumerate(client.results(search)):
            if i >= max_results:
                break
            results.append(
                {
                    "title": paper.title,
                    "url": paper.entry_id,
                    "snippet": (paper.summary or "")[:500],
                    "published_at": paper.published.isoformat() if paper.published else "",
                    "authors": [a.name for a in paper.authors[:8]],
                    "source": "arxiv",
                }
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("arXiv search failed: %s", exc)
    return results
