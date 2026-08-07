"""LangGraph pipeline state."""

from __future__ import annotations

import operator
from typing import Annotated, Any, NotRequired, TypedDict

from content_factory.models.schemas import (
    AnalyticsSnapshot,
    AssemblyPackage,
    ChangeLogEntry,
    PipelineMode,
    ResearchBrief,
    SEOPackage,
    StageName,
    StageStatus,
    TopicCandidate,
    VideoScript,
    VisualPackage,
    VoicePackage,
)


def merge_dicts(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


def append_list(left: list[Any], right: list[Any]) -> list[Any]:
    return list(left or []) + list(right or [])


class PipelineState(TypedDict):
    """Shared state flowing through the content factory graph."""

    run_id: str
    mode: str
    enabled_stages: list[str]
    topic_hint: NotRequired[str]
    headless: bool
    auto_approve: bool
    dry_run_media: bool

    topic_candidates: NotRequired[list[dict[str, Any]]]
    approved_topic: NotRequired[dict[str, Any] | None]
    research_brief: NotRequired[dict[str, Any] | None]
    script_draft: NotRequired[dict[str, Any] | None]
    script_final: NotRequired[dict[str, Any] | None]
    edit_changelog: NotRequired[list[dict[str, Any]]]
    voice_package: NotRequired[dict[str, Any] | None]
    visual_package: NotRequired[dict[str, Any] | None]
    assembly_package: NotRequired[dict[str, Any] | None]
    seo_package: NotRequired[dict[str, Any] | None]
    publish_results: NotRequired[list[dict[str, Any]]]
    analytics_snapshot: NotRequired[dict[str, Any] | None]

    approvals: Annotated[dict[str, Any], merge_dicts]
    stage_status: Annotated[dict[str, str], merge_dicts]
    errors: Annotated[list[str], append_list]
    messages: Annotated[list[str], append_list]


def initial_state(
    *,
    run_id: str,
    mode: PipelineMode | str,
    enabled_stages: list[StageName | str],
    topic_hint: str = "",
    headless: bool = False,
    auto_approve: bool = False,
    dry_run_media: bool = True,
) -> PipelineState:
    stage_names = [
        s.value if isinstance(s, StageName) else str(s) for s in enabled_stages
    ]
    return PipelineState(
        run_id=run_id,
        mode=mode.value if isinstance(mode, PipelineMode) else str(mode),
        enabled_stages=stage_names,
        topic_hint=topic_hint,
        headless=headless,
        auto_approve=auto_approve,
        dry_run_media=dry_run_media,
        topic_candidates=[],
        approved_topic=None,
        research_brief=None,
        script_draft=None,
        script_final=None,
        edit_changelog=[],
        voice_package=None,
        visual_package=None,
        assembly_package=None,
        seo_package=None,
        publish_results=[],
        analytics_snapshot=None,
        approvals={},
        stage_status={name: StageStatus.PENDING.value for name in stage_names},
        errors=[],
        messages=[],
    )


def stage_enabled(state: PipelineState, stage: StageName | str) -> bool:
    name = stage.value if isinstance(stage, StageName) else stage
    return name in state.get("enabled_stages", [])
