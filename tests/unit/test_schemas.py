from content_factory.models.schemas import (
    PipelineMode,
    StageName,
    TopicCandidate,
    TopicScores,
    VideoScript,
    ScriptSection,
    resolve_stages,
)


def test_topic_composite_inverts_competition():
    low_comp = TopicScores(
        virality=8, uniqueness=8, competition=2, channel_fit=8
    ).recompute()
    high_comp = TopicScores(
        virality=8, uniqueness=8, competition=9, channel_fit=8
    ).recompute()
    assert low_comp.composite > high_comp.composite


def test_resolve_stages_core():
    stages = resolve_stages(PipelineMode.CORE)
    assert StageName.DEEP_RESEARCH in stages
    assert StageName.SCRIPTWRITER in stages
    assert StageName.DISTRIBUTION not in stages


def test_resolve_stages_csv():
    stages = resolve_stages(PipelineMode.CUSTOM, "research,script")
    assert stages == [StageName.DEEP_RESEARCH, StageName.SCRIPTWRITER]


def test_script_recompute_stats():
    script = VideoScript(
        title_working="Test",
        topic_title="Test",
        sections=[
            ScriptSection(
                id="hook",
                title="Hook",
                narration="word " * 150,
            )
        ],
    ).recompute_stats(wpm=150)
    assert script.word_count == 150
    assert script.estimated_runtime_minutes == 1.0


def test_topic_candidate_roundtrip():
    c = TopicCandidate(
        title="Robot demo",
        summary="A demo",
        why_it_matters="Matters",
        scores=TopicScores(virality=7, uniqueness=6, competition=4, channel_fit=8),
    ).with_composite()
    data = c.model_dump(mode="json")
    c2 = TopicCandidate.model_validate(data)
    assert c2.title == "Robot demo"
    assert c2.scores.composite > 0
