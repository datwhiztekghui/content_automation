"""Deep Research — citation-rich research brief for an approved topic."""

from __future__ import annotations

import json
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import Citation, ResearchBrief, TopicCandidate
from content_factory.state import PipelineState
from content_factory.tools.arxiv_tool import search_arxiv
from content_factory.tools.llm import chat_json, LLMError
from content_factory.tools.web_search import search_web
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are the Deep Research Agent for a rigorous tech YouTube channel.

Produce a structured, citation-rich research brief. Be extremely accurate.
Rules:
- Prefer primary sources (papers, official blogs, company announcements).
- Never invent statistics, quotes, or URLs.
- If uncertain, put the claim in open_questions or uncertainty_flags.
- Include technical details, benchmarks when available, expert reactions, history, and implications.

Return JSON matching ResearchBrief:
{
  "topic_title": "...",
  "overview": "...",
  "technical_details": "...",
  "benchmarks": "...",
  "expert_reactions": "...",
  "historical_context": "...",
  "implications": "...",
  "open_questions": ["..."],
  "key_claims": ["..."],
  "citations": [{"title": "...", "url": "...", "publisher": "...", "published_at": "...", "note": "..."}],
  "uncertainty_flags": ["..."]
}
"""


def _collect_sources(topic: TopicCandidate, settings: Any) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for c in topic.sources:
        sources.append(
            {
                "title": c.title,
                "url": c.url,
                "snippet": c.note,
                "publisher": c.publisher,
                "source": "seed",
            }
        )
    queries = [
        topic.title,
        f"{topic.title} benchmarks",
        f"{topic.title} official announcement",
    ]
    for q in queries:
        sources.extend(search_web(q, max_results=6, settings=settings))
        sources.extend(search_arxiv(q, max_results=3))

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for s in sources:
        key = (s.get("url") or s.get("title") or "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(s)
    return unique[:40]


def brief_to_markdown(brief: ResearchBrief) -> str:
    lines = [
        f"# Research Brief: {brief.topic_title}\n",
        "## Overview\n",
        brief.overview,
        "\n## Technical Details\n",
        brief.technical_details,
        "\n## Benchmarks\n",
        brief.benchmarks or "_None gathered._",
        "\n## Expert Reactions\n",
        brief.expert_reactions or "_None gathered._",
        "\n## Historical Context\n",
        brief.historical_context or "_N/A_",
        "\n## Implications\n",
        brief.implications or "_N/A_",
        "\n## Key Claims\n",
    ]
    for claim in brief.key_claims:
        lines.append(f"- {claim}")
    lines.append("\n## Open Questions\n")
    for q in brief.open_questions:
        lines.append(f"- {q}")
    if brief.uncertainty_flags:
        lines.append("\n## Uncertainty Flags\n")
        for u in brief.uncertainty_flags:
            lines.append(f"- ⚠ {u}")
    lines.append("\n## Citations\n")
    for i, c in enumerate(brief.citations, 1):
        lines.append(f"{i}. [{c.title}]({c.url}) — {c.publisher} {c.note}")
    return "\n".join(lines)


def _heuristic_brief(topic: TopicCandidate, sources: list[dict[str, Any]]) -> ResearchBrief:
    cites = [
        Citation(
            title=s.get("title", ""),
            url=s.get("url", ""),
            publisher=s.get("publisher", s.get("source", "")),
            note=(s.get("snippet") or "")[:200],
        )
        for s in sources[:15]
    ]
    snippets = "\n".join(
        f"- {s.get('title')}: {(s.get('snippet') or '')[:240]}" for s in sources[:12]
    )
    return ResearchBrief(
        topic_title=topic.title,
        overview=topic.summary or topic.why_it_matters,
        technical_details=(
            "Automated brief (no LLM). Review source snippets below and expand manually.\n"
            + snippets
        ),
        benchmarks="",
        expert_reactions="",
        historical_context="",
        implications=topic.why_it_matters,
        open_questions=[
            "What are the independent benchmarks?",
            "What are the main limitations?",
        ],
        key_claims=[topic.why_it_matters] if topic.why_it_matters else [],
        citations=cites,
        uncertainty_flags=["Generated without LLM synthesis — verify all claims."],
    )


def run_deep_research(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "deep_research"
    try:
        raw_topic = state.get("approved_topic")
        if not raw_topic:
            return mark_failed(stage, "No approved_topic in state")

        topic = TopicCandidate.model_validate(raw_topic)
        log.info("Deep Research on: %s", topic.title)
        sources = _collect_sources(topic, ctx.settings)

        if ctx.use_llm:
            try:
                user = {
                    "topic": topic.model_dump(mode="json"),
                    "gathered_sources": sources,
                    "instructions": (
                        "Synthesize a rigorous brief. Only cite URLs present in gathered_sources "
                        "or the topic seed sources. Flag gaps explicitly."
                    ),
                }
                data = chat_json(
                    SYSTEM_PROMPT,
                    json.dumps(user, ensure_ascii=False, default=str),
                    settings=ctx.settings,
                    temperature=0.25,
                    max_tokens=8192,
                )
                brief = ResearchBrief.model_validate(data)
            except (LLMError, Exception) as exc:  # noqa: BLE001
                log.warning("LLM research failed (%s); heuristic brief", exc)
                brief = _heuristic_brief(topic, sources)
        else:
            brief = _heuristic_brief(topic, sources)

        ctx.store.write_json("research/brief.json", brief)
        ctx.store.write_text("research/brief.md", brief_to_markdown(brief))
        ctx.store.write_json("research/sources_raw.json", sources)

        return mark_done(stage, {"research_brief": brief.model_dump(mode="json")})
    except Exception as exc:  # noqa: BLE001
        log.exception("Deep Research failed")
        return mark_failed(stage, str(exc))
