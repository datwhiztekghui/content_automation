"""Trend Scout — discover and rank high-potential video topics."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import Citation, TopicCandidate, TopicScores
from content_factory.state import PipelineState
from content_factory.tools.arxiv_tool import search_arxiv
from content_factory.tools.llm import chat_json, LLMError
from content_factory.tools.news_feeds import fetch_recent_headlines
from content_factory.tools.web_search import search_web
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are the Trend Scout Agent for a YouTube channel covering tech, inventions,
robotics, AI breakthroughs, science, and related news.

Tone of the channel: excited but analytical, clear, authoritative, accessible.

Your job: from raw signals (headlines, papers, search hits), propose high-potential video topics.
Score each on:
- virality (0-10): shareability and curiosity gap
- uniqueness (0-10): fresh angle / under-covered
- competition (0-10): higher means MORE similar videos already (worse)
- channel_fit (0-10): fit for tech/robotics/AI/science explainers

Return JSON:
{
  "candidates": [
    {
      "title": "...",
      "summary": "...",
      "why_it_matters": "...",
      "suggested_angle": "...",
      "keywords": ["..."],
      "sources": [{"title": "...", "url": "...", "publisher": "...", "note": "..."}],
      "scores": {"virality": 0, "uniqueness": 0, "competition": 0, "channel_fit": 0}
    }
  ]
}

Propose 5-8 candidates. Prefer primary, timely stories. No invented URLs — only use provided sources.
"""


class _ScoutOut(BaseModel):
    candidates: list[dict[str, Any]] = Field(default_factory=list)


def _gather_signals(topic_hint: str, settings: Any) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    signals.extend(fetch_recent_headlines(per_feed=4))

    queries = [
        "AI breakthrough OR robotics OR invention news",
        "large language model release OR robot demo science",
    ]
    if topic_hint:
        queries.insert(0, topic_hint)

    for q in queries[:3]:
        signals.extend(search_web(q, max_results=5, settings=settings))
        signals.extend(search_arxiv(q, max_results=3))

    # Dedupe by URL/title
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for s in signals:
        key = (s.get("url") or s.get("title") or "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(s)
    return unique[:60]


def _candidates_from_llm(
    signals: list[dict[str, Any]],
    topic_hint: str,
    style: dict[str, Any],
    settings: Any,
) -> list[TopicCandidate]:
    weights = (style.get("scoring_weights") or {}) if style else {}
    user = {
        "channel": style.get("channel_name", "Tech Frontier"),
        "topic_hint": topic_hint or None,
        "topic_fit": style.get("topic_fit"),
        "signals": signals[:40],
    }
    data = chat_json(
        SYSTEM_PROMPT,
        json.dumps(user, ensure_ascii=False, default=str),
        settings=settings,
        temperature=0.5,
    )
    raw_list = data.get("candidates") if isinstance(data, dict) else data
    if not isinstance(raw_list, list):
        raise LLMError("Trend Scout expected candidates list in JSON")

    out: list[TopicCandidate] = []
    for item in raw_list:
        try:
            scores = TopicScores(
                virality=float(item.get("scores", {}).get("virality", 5)),
                uniqueness=float(item.get("scores", {}).get("uniqueness", 5)),
                competition=float(item.get("scores", {}).get("competition", 5)),
                channel_fit=float(item.get("scores", {}).get("channel_fit", 5)),
            )
            sources = [
                Citation(
                    title=s.get("title", ""),
                    url=s.get("url", ""),
                    publisher=s.get("publisher", ""),
                    note=s.get("note", ""),
                )
                for s in item.get("sources", [])
                if isinstance(s, dict)
            ]
            cand = TopicCandidate(
                title=item["title"],
                summary=item.get("summary", ""),
                why_it_matters=item.get("why_it_matters", ""),
                suggested_angle=item.get("suggested_angle", ""),
                keywords=item.get("keywords", []) or [],
                sources=sources,
                scores=scores,
            ).with_composite(weights)
            out.append(cand)
        except Exception as exc:  # noqa: BLE001
            log.warning("Skipping invalid candidate: %s", exc)
    out.sort(key=lambda c: c.scores.composite, reverse=True)
    return out


def _fallback_from_signals(
    signals: list[dict[str, Any]],
    topic_hint: str,
    style: dict[str, Any],
) -> list[TopicCandidate]:
    """Offline/heuristic ranking when LLM is unavailable."""
    weights = style.get("scoring_fit") if False else style.get("scoring_weights")
    candidates: list[TopicCandidate] = []
    if topic_hint:
        candidates.append(
            TopicCandidate(
                title=topic_hint,
                summary=f"User-requested topic: {topic_hint}",
                why_it_matters="Explicit editorial priority from the operator.",
                suggested_angle=f"Explain what {topic_hint} is, why it matters now, and implications.",
                sources=[],
                scores=TopicScores(
                    virality=7, uniqueness=7, competition=5, channel_fit=9
                ),
            ).with_composite(weights)
        )
    for i, s in enumerate(signals[:8]):
        title = s.get("title") or f"Topic signal {i+1}"
        candidates.append(
            TopicCandidate(
                title=title,
                summary=(s.get("snippet") or "")[:400],
                why_it_matters="Appearing across recent tech/science feeds — potential audience interest.",
                suggested_angle="Deep explainer with benchmarks and implications.",
                sources=[
                    Citation(
                        title=title,
                        url=s.get("url", ""),
                        publisher=s.get("publisher", s.get("source", "")),
                    )
                ],
                scores=TopicScores(
                    virality=6,
                    uniqueness=5,
                    competition=5,
                    channel_fit=7,
                ),
            ).with_composite(weights)
        )
    candidates.sort(key=lambda c: c.scores.composite, reverse=True)
    return candidates


def topics_to_markdown(candidates: list[TopicCandidate]) -> str:
    lines = ["# Topic Candidates\n"]
    for i, c in enumerate(candidates, 1):
        lines.append(f"## {i}. {c.title}")
        lines.append(f"**Composite score:** {c.scores.composite}/10")
        lines.append(
            f"- Virality: {c.scores.virality} | Uniqueness: {c.scores.uniqueness} | "
            f"Competition: {c.scores.competition} | Channel fit: {c.scores.channel_fit}"
        )
        lines.append(f"\n{c.summary}\n")
        lines.append(f"**Why it matters:** {c.why_it_matters}")
        if c.suggested_angle:
            lines.append(f"\n**Suggested angle:** {c.suggested_angle}")
        if c.sources:
            lines.append("\n**Sources:**")
            for s in c.sources:
                lines.append(f"- [{s.title}]({s.url}) {s.publisher}")
        lines.append("")
    return "\n".join(lines)


def run_trend_scout(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "trend_scout"
    try:
        topic_hint = state.get("topic_hint") or ""
        log.info("Trend Scout gathering signals (hint=%r)", topic_hint)
        signals = _gather_signals(topic_hint, ctx.settings)

        if ctx.use_llm:
            try:
                candidates = _candidates_from_llm(
                    signals, topic_hint, ctx.style, ctx.settings
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM trend scout failed (%s); using fallback", exc)
                candidates = _fallback_from_signals(signals, topic_hint, ctx.style)
        else:
            log.warning("No LLM available — using heuristic topic ranking (install Ollama for free)")
            candidates = _fallback_from_signals(signals, topic_hint, ctx.style)

        if not candidates and topic_hint:
            candidates = _fallback_from_signals([], topic_hint, ctx.style)

        payload = [c.model_dump(mode="json") for c in candidates]
        ctx.store.write_json("topics/candidates.json", payload)
        ctx.store.write_text("topics/candidates.md", topics_to_markdown(candidates))

        # If topic hint provided and scout runs, pre-select best match later in await_topic
        return mark_done(
            stage,
            {
                "topic_candidates": payload,
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Trend Scout failed")
        return mark_failed(stage, str(exc))
