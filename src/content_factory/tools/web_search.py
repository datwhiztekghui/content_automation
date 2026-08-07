"""Web search adapters — paid keys optional; DuckDuckGo is free default."""

from __future__ import annotations

from typing import Any

import httpx

from config.settings import Settings, get_settings
from content_factory.utils.logging import get_logger

log = get_logger(__name__)


def search_web(
    query: str,
    *,
    max_results: int = 8,
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Return list of {title, url, snippet, source}."""
    settings = settings or get_settings()
    provider = settings.resolve_search_provider()

    if provider == "none":
        return []
    if provider == "tavily" and settings.tavily_api_key:
        return _tavily(query, max_results, settings.tavily_api_key)
    if provider == "serper" and settings.serper_api_key:
        return _serper(query, max_results, settings.serper_api_key)
    if provider == "brave" and settings.brave_api_key:
        return _brave(query, max_results, settings.brave_api_key)

    # Free path: DuckDuckGo → Wikipedia
    results = _duckduckgo(query, max_results)
    if results:
        return results
    wiki = _wikipedia(query, max_results=min(3, max_results))
    if wiki:
        return wiki
    log.warning("Free search returned no results for %r", query)
    return []


def _duckduckgo(query: str, max_results: int) -> list[dict[str, Any]]:
    ddgs_cls = None
    try:
        from ddgs import DDGS as ddgs_cls  # type: ignore
    except ImportError:
        try:
            from duckduckgo_search import DDGS as ddgs_cls  # type: ignore
        except ImportError:
            log.warning(
                "Free search package missing — run: pip install ddgs"
            )
            return _wikipedia(query, max_results=min(3, max_results))

    results: list[dict[str, Any]] = []
    try:
        client = ddgs_cls()
        # Support context-manager and plain client APIs
        if hasattr(client, "__enter__"):
            client = client.__enter__()
        try:
            for item in client.text(query, max_results=max_results):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href") or item.get("link", ""),
                        "snippet": item.get("body") or item.get("snippet", ""),
                        "source": "duckduckgo",
                    }
                )
        finally:
            if hasattr(client, "__exit__"):
                client.__exit__(None, None, None)
    except Exception as exc:  # noqa: BLE001
        log.warning("DuckDuckGo search failed: %s", exc)
        return _wikipedia(query, max_results=min(3, max_results))
    return results[:max_results]


def _wikipedia(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """Free Wikipedia OpenSearch + summary (no API key)."""
    results: list[dict[str, Any]] = []
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            search = client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "opensearch",
                    "search": query,
                    "limit": max_results,
                    "namespace": 0,
                    "format": "json",
                },
                headers={"User-Agent": "ContentFactory/0.1 (free research bot)"},
            )
            search.raise_for_status()
            data = search.json()
            # [query, [titles], [descriptions], [urls]]
            titles = data[1] if len(data) > 1 else []
            descs = data[2] if len(data) > 2 else []
            urls = data[3] if len(data) > 3 else []
            for i, title in enumerate(titles):
                results.append(
                    {
                        "title": title,
                        "url": urls[i] if i < len(urls) else "",
                        "snippet": descs[i] if i < len(descs) else "",
                        "source": "wikipedia",
                    }
                )
    except Exception as exc:  # noqa: BLE001
        log.warning("Wikipedia search failed: %s", exc)
    return results


def _tavily(query: str, max_results: int, api_key: str) -> list[dict[str, Any]]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data.get("results", [])[:max_results]:
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "source": "tavily",
            }
        )
    return results


def _serper(query: str, max_results: int, api_key: str) -> list[dict[str, Any]]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": max_results},
        )
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data.get("organic", [])[:max_results]:
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "source": "serper",
            }
        )
    return results


def _brave(query: str, max_results: int, api_key: str) -> list[dict[str, Any]]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
            params={"q": query, "count": max_results},
        )
        resp.raise_for_status()
        data = resp.json()
    results = []
    for item in data.get("web", {}).get("results", [])[:max_results]:
        results.append(
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "source": "brave",
            }
        )
    return results
