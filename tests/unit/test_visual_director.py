from content_factory.agents.visual_director.agent import (
    TARGET_SHOT_SECONDS,
    _enrich_prompt,
    _heuristic_dense_visuals,
)
from content_factory.models.schemas import ScriptSection, VideoScript


def _sample_script(minutes: float = 11.0) -> VideoScript:
    # ~150 wpm * minutes
    words = int(150 * minutes)
    sections = [
        ScriptSection(
            id="hook",
            title="Hook",
            start_timestamp="00:00",
            end_timestamp="00:25",
            narration="word " * 40,
            visual_cues=["cold open"],
        ),
        ScriptSection(
            id="why_it_matters",
            title="Why",
            start_timestamp="00:25",
            end_timestamp="02:30",
            narration="word " * 200,
        ),
        ScriptSection(
            id="explanation",
            title="How",
            start_timestamp="02:30",
            end_timestamp="07:00",
            narration="word " * 400,
        ),
        ScriptSection(
            id="benchmarks_demos",
            title="Proof",
            start_timestamp="07:00",
            end_timestamp="10:00",
            narration="word " * 300,
        ),
        ScriptSection(
            id="implications",
            title="Implications",
            start_timestamp="10:00",
            end_timestamp="12:00",
            narration="word " * 250,
        ),
        ScriptSection(
            id="bigger_picture",
            title="Bigger",
            start_timestamp="12:00",
            end_timestamp="13:30",
            narration="word " * 150,
        ),
        ScriptSection(
            id="cta",
            title="CTA",
            start_timestamp="13:30",
            end_timestamp="14:30",
            narration="word " * 80,
        ),
    ]
    return VideoScript(
        title_working="Test Topic",
        topic_title="Test Topic Meta Court Ruling",
        sections=sections,
        word_count=words,
        estimated_runtime_minutes=minutes,
    ).recompute_stats()


def test_dense_shots_for_long_form():
    script = _sample_script(11)
    pkg = _heuristic_dense_visuals(script)
    # ~11 min / 6s ≈ 110 shots; allow some slack
    assert len(pkg.shot_list) >= 80
    assert len(pkg.broll_prompts) == len(pkg.shot_list)
    assert len(pkg.thumbnail_concepts) >= 5


def test_prompts_photoreal_no_text_watermark_cues():
    script = _sample_script(10)
    pkg = _heuristic_dense_visuals(script)
    sample = pkg.broll_prompts[0]["prompt"].lower()
    assert "photoreal" in sample or "photorealistic" in sample
    assert "watermark" in sample
    assert "no text" in sample or "text overlay" in sample


def test_enrich_prompt_appends_quality_bar():
    out = _enrich_prompt("A courthouse exterior at dusk", "topic")
    assert "photoreal" in out.lower() or "photorealistic" in out.lower()
    assert "watermark" in out.lower()


def test_target_shot_pace():
    assert TARGET_SHOT_SECONDS <= 8.0
