"""Human-in-the-loop approval gates (interactive + headless file-based)."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import TopicCandidate, TopicScores
from content_factory.state import PipelineState
from content_factory.utils.logging import get_logger

log = get_logger(__name__)
console = Console()


def _pick_topic_from_hint(
    candidates: list[dict[str, Any]], hint: str
) -> dict[str, Any] | None:
    if not hint:
        return None
    lower = hint.lower()
    for c in candidates:
        if lower in (c.get("title") or "").lower():
            return c
    # Fabricate approved topic from hint if no match
    return TopicCandidate(
        title=hint,
        summary=f"Operator-selected topic: {hint}",
        why_it_matters="Selected directly by the operator.",
        suggested_angle=f"Deep explainer on {hint}",
        scores=TopicScores(
            virality=7, uniqueness=7, competition=5, channel_fit=9
        ),
    ).with_composite().model_dump(mode="json")


def await_topic_approval(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "await_topic"
    candidates = list(state.get("topic_candidates") or [])
    hint = state.get("topic_hint") or ""
    auto = state.get("auto_approve", False)
    headless = state.get("headless", False)

    # Forced topic without scout candidates
    if not candidates and hint:
        topic = _pick_topic_from_hint([], hint)
        ctx.store.write_json("approvals/topic.json", {"approved": topic, "via": "topic_hint"})
        return mark_done(
            stage,
            {
                "approved_topic": topic,
                "approvals": {"topic": True, "topic_via": "hint"},
            },
        )

    if not candidates:
        return mark_failed(stage, "No topic candidates to approve")

    # Auto-approve top candidate
    if auto:
        topic = candidates[0]
        if hint:
            topic = _pick_topic_from_hint(candidates, hint) or topic
        ctx.store.write_json(
            "approvals/topic.json", {"approved": topic, "via": "auto_approve"}
        )
        return mark_done(
            stage,
            {
                "approved_topic": topic,
                "approvals": {"topic": True, "topic_via": "auto"},
            },
        )

    # Headless: write pending file and check for approval response
    if headless:
        pending = {
            "type": "topic",
            "status": "pending",
            "candidates": candidates,
            "instructions": (
                "Write approvals/topic_decision.json with "
                '{"approve_index": 0} or {"title": "..."} or {"approve": true} for top.'
            ),
        }
        ctx.store.write_json("approvals/pending_topic.json", pending)
        decision = ctx.store.read_json("approvals/topic_decision.json")
        if not decision:
            # Pause semantics: mark awaiting — graph runner should stop
            return {
                "stage_status": {stage: "awaiting_approval"},
                "messages": [
                    "Headless topic approval pending. "
                    f"Write decision to {ctx.store.path('approvals/topic_decision.json')}"
                ],
                "approvals": {"topic": False, "topic_pending": True},
            }
        topic = _resolve_topic_decision(candidates, decision, hint)
        ctx.store.write_json(
            "approvals/topic.json", {"approved": topic, "via": "headless_file"}
        )
        return mark_done(
            stage,
            {
                "approved_topic": topic,
                "approvals": {"topic": True, "topic_via": "file"},
            },
        )

    # Interactive CLI
    table = Table(title="Topic Candidates")
    table.add_column("#", style="cyan")
    table.add_column("Score")
    table.add_column("Title")
    table.add_column("Why it matters")
    for i, c in enumerate(candidates):
        scores = c.get("scores") or {}
        table.add_row(
            str(i),
            str(scores.get("composite", "?")),
            (c.get("title") or "")[:60],
            (c.get("why_it_matters") or "")[:80],
        )
    console.print(table)
    if hint:
        console.print(f"[yellow]Topic hint:[/yellow] {hint}")

    console.print(
        "Enter index to approve, or type a custom topic title "
        "(or 'q' to abort):"
    )
    try:
        choice = input("> ").strip()
    except EOFError:
        choice = "0"

    if choice.lower() in {"q", "quit", "abort"}:
        return mark_failed(stage, "Topic approval aborted by user")

    if choice.isdigit() and int(choice) < len(candidates):
        topic = candidates[int(choice)]
    elif choice:
        topic = _pick_topic_from_hint(candidates, choice) or TopicCandidate(
            title=choice,
            summary=f"Custom topic: {choice}",
            why_it_matters="Operator custom selection.",
        ).model_dump(mode="json")
    else:
        topic = candidates[0]

    ctx.store.write_json(
        "approvals/topic.json", {"approved": topic, "via": "interactive"}
    )
    console.print(f"[green]Approved topic:[/green] {topic.get('title')}")
    return mark_done(
        stage,
        {
            "approved_topic": topic,
            "approvals": {"topic": True, "topic_via": "interactive"},
        },
    )


def _resolve_topic_decision(
    candidates: list[dict[str, Any]],
    decision: dict[str, Any],
    hint: str,
) -> dict[str, Any]:
    if "approve_index" in decision:
        idx = int(decision["approve_index"])
        return candidates[max(0, min(idx, len(candidates) - 1))]
    if decision.get("title"):
        return _pick_topic_from_hint(candidates, decision["title"]) or candidates[0]
    if decision.get("approve") is True:
        return _pick_topic_from_hint(candidates, hint) or candidates[0]
    return candidates[0]


def await_script_approval(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "await_script"
    script = state.get("script_final") or state.get("script_draft")
    if not script:
        return mark_failed(stage, "No script to approve")

    auto = state.get("auto_approve", False)
    headless = state.get("headless", False)

    if auto:
        ctx.store.write_json(
            "approvals/script.json", {"approved": True, "via": "auto_approve"}
        )
        return mark_done(stage, {"approvals": {"script": True, "script_via": "auto"}})

    if headless:
        ctx.store.write_json(
            "approvals/pending_script.json",
            {
                "type": "script",
                "status": "pending",
                "path": "script/final.md",
                "instructions": (
                    'Write approvals/script_decision.json with {"approve": true}'
                ),
            },
        )
        decision = ctx.store.read_json("approvals/script_decision.json")
        if not decision or not decision.get("approve"):
            return {
                "stage_status": {stage: "awaiting_approval"},
                "messages": [
                    "Headless script approval pending. "
                    f"Write {ctx.store.path('approvals/script_decision.json')}"
                ],
                "approvals": {"script": False, "script_pending": True},
            }
        ctx.store.write_json(
            "approvals/script.json", {"approved": True, "via": "headless_file"}
        )
        return mark_done(stage, {"approvals": {"script": True, "script_via": "file"}})

    # Interactive
    title = script.get("title_working") or script.get("topic_title")
    words = script.get("word_count")
    runtime = script.get("estimated_runtime_minutes")
    console.print(
        f"\n[bold]Script ready for approval[/bold]\n"
        f"Title: {title}\nWords: {words} | Est. runtime: {runtime} min\n"
        f"Preview path: {ctx.store.path('script/final.md')}\n"
    )
    console.print("Approve script? [Y/n]")
    try:
        ans = input("> ").strip().lower()
    except EOFError:
        ans = "y"
    if ans in {"", "y", "yes"}:
        ctx.store.write_json(
            "approvals/script.json", {"approved": True, "via": "interactive"}
        )
        return mark_done(
            stage, {"approvals": {"script": True, "script_via": "interactive"}}
        )
    return mark_failed(stage, "Script rejected by user")
