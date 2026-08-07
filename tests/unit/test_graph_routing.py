from content_factory.graph import STAGE_ORDER, build_graph
from content_factory.models.schemas import StageName, resolve_stages, PipelineMode
from content_factory.state import initial_state, stage_enabled


def test_stage_enabled():
    state = initial_state(
        run_id="test",
        mode=PipelineMode.CORE,
        enabled_stages=[StageName.SCRIPTWRITER],
    )
    assert stage_enabled(state, StageName.SCRIPTWRITER)
    assert not stage_enabled(state, StageName.DISTRIBUTION)


def test_build_graph_compiles():
    stages = [s.value for s in resolve_stages(PipelineMode.SCOUT)]
    graph = build_graph(stages)
    assert graph is not None


def test_stage_order_covers_all_agents():
    assert "trend_scout" in STAGE_ORDER
    assert "analytics" in STAGE_ORDER
    assert STAGE_ORDER.index("trend_scout") < STAGE_ORDER.index("deep_research")
    assert STAGE_ORDER.index("scriptwriter") < STAGE_ORDER.index("fact_checker")
