"""Shared agent utilities."""

from __future__ import annotations

from typing import Any

from config.settings import Settings, get_settings
from content_factory.state import PipelineState
from content_factory.tools.llm import llm_available
from content_factory.utils.artifacts import ArtifactStore
from content_factory.utils.logging import get_logger

log = get_logger(__name__)


class AgentContext:
    def __init__(
        self,
        state: PipelineState,
        settings: Settings | None = None,
        store: ArtifactStore | None = None,
    ) -> None:
        self.state = state
        self.settings = settings or get_settings()
        self.store = store or ArtifactStore(
            self.settings.runs_dir, state["run_id"]
        )
        self.style = self.settings.load_channel_style()

    @property
    def use_llm(self) -> bool:
        return llm_available(self.settings)


def mark_running(state: PipelineState, stage: str) -> dict[str, Any]:
    return {"stage_status": {stage: "running"}, "messages": [f"Starting {stage}"]}


def mark_done(stage: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "stage_status": {stage: "completed"},
        "messages": [f"Completed {stage}"],
    }
    if extra:
        payload.update(extra)
    return payload


def mark_skipped(stage: str, reason: str = "") -> dict[str, Any]:
    msg = f"Skipped {stage}" + (f": {reason}" if reason else "")
    return {"stage_status": {stage: "skipped"}, "messages": [msg]}


def mark_failed(stage: str, error: str) -> dict[str, Any]:
    return {
        "stage_status": {stage: "failed"},
        "errors": [f"{stage}: {error}"],
        "messages": [f"Failed {stage}: {error}"],
    }
