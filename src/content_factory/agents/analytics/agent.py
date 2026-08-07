"""Analytics & Learning — performance insights for future runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import AnalyticsSnapshot
from content_factory.state import PipelineState
from content_factory.utils.logging import get_logger

log = get_logger(__name__)


def run_analytics(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "analytics"
    try:
        # Manual import path: data/runs/<id>/analytics/manual_metrics.json
        manual = ctx.store.read_json("analytics/manual_metrics.json") or {}
        snapshot = AnalyticsSnapshot(
            video_id=manual.get("video_id", ""),
            views=int(manual.get("views", 0)),
            watch_time_hours=float(manual.get("watch_time_hours", 0)),
            avg_view_duration_seconds=float(
                manual.get("avg_view_duration_seconds", 0)
            ),
            ctr=float(manual.get("ctr", 0)),
            likes=int(manual.get("likes", 0)),
            comments=int(manual.get("comments", 0)),
            insights=manual.get("insights")
            or [
                "No live YouTube Analytics connected yet.",
                "Drop metrics into analytics/manual_metrics.json and re-run --mode analytics.",
                "High-retention hooks and concrete benchmarks correlate with stronger CTR/AVD — prioritize those in Trend Scout scoring.",
            ],
        )
        ctx.store.write_json("analytics/snapshot.json", snapshot)

        # Append to global learnings store
        learnings_dir: Path = ctx.settings.learnings_dir
        learnings_dir.mkdir(parents=True, exist_ok=True)
        learnings_path = learnings_dir / "insights.jsonl"
        record = {
            "run_id": state["run_id"],
            "topic": (state.get("approved_topic") or {}).get("title"),
            "snapshot": snapshot.model_dump(mode="json"),
        }
        with learnings_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

        return mark_done(
            stage, {"analytics_snapshot": snapshot.model_dump(mode="json")}
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Analytics failed")
        return mark_failed(stage, str(exc))
