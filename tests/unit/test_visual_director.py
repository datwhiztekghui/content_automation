from content_factory.agents.visual_director.agent import (
    TARGET_SHOT_SECONDS,
    _build_grounded_package,
    _detect_story_profile,
    _enrich_prompt,
    _meta_nm_story_pack,
)
from content_factory.models.schemas import ScriptSection, VideoScript


def _sample_script(topic: str = "Meta Public Nuisance Ruling $567 Million") -> VideoScript:
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
        title_working=topic,
        topic_title=topic,
        sections=sections,
        word_count=1500,
        estimated_runtime_minutes=11.0,
    ).recompute_stats()


def test_detect_meta_profile():
    g = {
        "brief_overview": "New Mexico public nuisance Meta child safety",
        "brief_claims": ["$567 million"],
        "news_hits": [{"title": "Meta New Mexico", "snippet": "public nuisance"}],
    }
    assert (
        _detect_story_profile("Meta public nuisance $567M", g)
        == "meta_nm_child_safety_public_nuisance"
    )


def test_meta_pack_has_story_links():
    pack = _meta_nm_story_pack()
    assert len(pack["seeds"]) >= 8
    assert all(s.get("story_link") for s in pack["seeds"])
    assert any("567" in b["fact"] or "375" in b["fact"] for b in pack["beats"])


def test_grounded_package_dense_and_linked():
    script = _sample_script()
    grounding = {
        "brief_overview": "Meta New Mexico child safety public nuisance",
        "brief_claims": [],
        "news_hits": [],
        "uncertainty_flags": [],
    }
    pkg, extras = _build_grounded_package(
        script, grounding, "meta_nm_child_safety_public_nuisance"
    )
    assert len(pkg.shot_list) >= 80
    assert all(s.get("story_link") for s in pkg.shot_list)
    assert all(b.get("story_link") for b in pkg.broll_prompts)
    assert extras.get("creative_strategy", {}).get("story_one_liner")
    # No random unlinked server-only prompts without story_link
    assert "New Mexico" in (extras["creative_strategy"]["story_one_liner"] or "")


def test_enrich_prompt():
    out = _enrich_prompt("New Mexico courthouse exterior")
    assert "photoreal" in out.lower() or "photorealistic" in out.lower()
    assert "watermark" in out.lower()


def test_target_shot_pace():
    assert TARGET_SHOT_SECONDS <= 8.0
