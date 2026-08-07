"""LangGraph pipeline orchestration with modular stages."""

from __future__ import annotations

from typing import Any, Callable

from langgraph.graph import END, START, StateGraph

from content_factory.agents.analytics import run_analytics
from content_factory.agents.deep_research import run_deep_research
from content_factory.agents.distribution import run_distribution
from content_factory.agents.fact_checker import run_fact_checker
from content_factory.agents.scriptwriter import run_scriptwriter
from content_factory.agents.seo_packaging import run_seo_packaging
from content_factory.agents.trend_scout import run_trend_scout
from content_factory.agents.video_assembler import run_video_assembler
from content_factory.agents.visual_director import run_visual_director
from content_factory.agents.voice_director import run_voice_director
from content_factory.gates.approval import await_script_approval, await_topic_approval
from content_factory.models.schemas import StageName
from content_factory.state import PipelineState, stage_enabled
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

NODE_FNS: dict[str, Callable[[PipelineState], dict[str, Any]]] = {
    StageName.TREND_SCOUT.value: run_trend_scout,
    StageName.AWAIT_TOPIC.value: await_topic_approval,
    StageName.DEEP_RESEARCH.value: run_deep_research,
    StageName.SCRIPTWRITER.value: run_scriptwriter,
    StageName.FACT_CHECKER.value: run_fact_checker,
    StageName.AWAIT_SCRIPT.value: await_script_approval,
    StageName.VOICE_DIRECTOR.value: run_voice_director,
    StageName.VISUAL_DIRECTOR.value: run_visual_director,
    StageName.VIDEO_ASSEMBLER.value: run_video_assembler,
    StageName.SEO_PACKAGING.value: run_seo_packaging,
    StageName.DISTRIBUTION.value: run_distribution,
    StageName.ANALYTICS.value: run_analytics,
}

# Canonical order for sequencing enabled stages
STAGE_ORDER: list[str] = [s.value for s in StageName]


def _wrap(stage: str, fn: Callable[[PipelineState], dict[str, Any]]):
    def node(state: PipelineState) -> dict[str, Any]:
        if not stage_enabled(state, stage):
            log.info("Skipping disabled stage %s", stage)
            return {
                "stage_status": {stage: "skipped"},
                "messages": [f"Skipped {stage} (not enabled)"],
            }
        log.info(">>> Running stage: %s", stage)
        result = fn(state)
        # Stop graph early if awaiting approval in headless mode
        return result

    return node


def build_graph(enabled_stages: list[str] | None = None):
    """Build a linear graph over the enabled stages (canonical order)."""
    builder: StateGraph = StateGraph(PipelineState)

    # Always register all nodes so the same graph can skip via stage_enabled
    for name, fn in NODE_FNS.items():
        builder.add_node(name, _wrap(name, fn))

    # Linear edges in canonical order; routing at runtime skips disabled
    ordered = [s for s in STAGE_ORDER if s in NODE_FNS]
    if enabled_stages:
        # Preserve canonical order but only chain enabled ones
        ordered = [s for s in STAGE_ORDER if s in enabled_stages]

    if not ordered:
        raise ValueError("No stages enabled for graph")

    builder.add_edge(START, ordered[0])
    for a, b in zip(ordered, ordered[1:]):
        builder.add_edge(a, b)
    builder.add_edge(ordered[-1], END)

    return builder.compile()


def run_pipeline(state: PipelineState) -> PipelineState:
    """Execute the pipeline for the given initial state."""
    enabled = list(state.get("enabled_stages") or [])
    graph = build_graph(enabled)
    log.info(
        "Pipeline start run_id=%s mode=%s stages=%s",
        state.get("run_id"),
        state.get("mode"),
        enabled,
    )
    final: PipelineState = graph.invoke(state)
    log.info("Pipeline finished run_id=%s", state.get("run_id"))
    return final
