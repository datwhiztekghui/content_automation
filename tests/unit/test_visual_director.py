from content_factory.agents.visual_director.agent import (
    BODY_SHOT_SECONDS,
    HOOK_SHOT_SECONDS,
    _build_competitive_package,
    _facts_from_grounding,
)
from content_factory.agents.visual_director.identity_assets import (
    extract_entities,
    build_identity_capture_plan,
    thumbnail_concepts_with_identity,
)
from content_factory.agents.visual_director.peer_style import (
    STYLE_LOCK,
    cinematic_for_topic,
    motion_graphic_recipes,
    studio_reference_manifest,
    studio_reference_paths,
)
from content_factory.agents.visual_director.studio_layout import (
    article_card_prompt,
    panel_for_asset,
    studio_layout_manifest,
)
from content_factory.models.schemas import ScriptSection, VideoScript


def _script() -> VideoScript:
    sections = [
        ScriptSection(
            id="hook",
            title="Hook",
            start_timestamp="00:00",
            end_timestamp="00:30",
            narration="word " * 50,
        ),
        ScriptSection(
            id="why_it_matters",
            title="Why",
            start_timestamp="00:30",
            end_timestamp="03:00",
            narration="word " * 250,
        ),
        ScriptSection(
            id="explanation",
            title="How",
            start_timestamp="03:00",
            end_timestamp="08:00",
            narration="word " * 400,
        ),
        ScriptSection(
            id="cta",
            title="CTA",
            start_timestamp="08:00",
            end_timestamp="09:00",
            narration="word " * 80,
        ),
    ]
    return VideoScript(
        title_working="Meta Public Nuisance $567M",
        topic_title="Meta New Mexico public nuisance ruling",
        sections=sections,
        estimated_runtime_minutes=11.0,
        word_count=1600,
    )


def test_peer_pace_faster_than_old_doc_style():
    assert HOOK_SHOT_SECONDS <= 3.5
    assert BODY_SHOT_SECONDS <= 6.0


def test_style_lock_is_virtual_studio():
    assert "Chloe" in STYLE_LOCK
    assert "glass" in STYLE_LOCK.lower()
    assert "AIInfoRoom" in STYLE_LOCK
    assert "SCENIUM" not in STYLE_LOCK or "not SCENIUM" in STYLE_LOCK


def test_competitive_package_has_mixed_asset_classes():
    script = _script()
    grounding = {
        "brief_overview": "Meta New Mexico child safety public nuisance",
        "brief_claims": [],
        "news_hits": [{"title": "BBC Meta", "url": "https://bbc.com", "snippet": "567"}],
    }
    pkg, extras = _build_competitive_package(script, grounding, {})
    classes = {s.get("asset_class") for s in pkg.shot_list}
    assert "kinetic_stat" in classes
    assert "cinematic_broll" in classes
    assert "ui_screen" in classes
    assert "logo_card" in classes
    assert "person_plate" in classes
    assert len(pkg.shot_list) >= 40
    assert extras.get("motion_graphics")
    assert extras.get("screen_captures")
    assert extras.get("identity_captures")
    assert extras["identity_captures"].get("person_captures")
    assert extras["identity_captures"].get("logo_captures")
    assert extras.get("channel_visual_style") == "virtual_studio_anchor"
    assert extras.get("studio_layout")
    # thumbs require identity / studio language
    assert any(
        "Chloe" in (t.visual_description or "")
        or "REAL" in (t.visual_description or "")
        or "captured" in (t.visual_description or "").lower()
        for t in pkg.thumbnail_concepts
    )
    # cinematic prompts mention Chloe / studio
    cines = [
        b for b in pkg.broll_prompts if b.get("asset_class") == "cinematic_broll"
    ]
    assert cines
    assert any("Chloe" in (b.get("prompt") or "") for b in cines)


def test_extract_meta_entities():
    ents = extract_entities("Meta Muse Code AI agent", "Mark Zuckerberg Meta")
    assert any(e["company"] == "Meta" for e in ents)
    plan = build_identity_capture_plan("Meta Muse Code", ents, [])
    assert plan["logo_captures"]
    assert any("Zuckerberg" in p["name"] for p in plan["person_captures"])
    assert any(
        "glass" in " ".join(p.get("use_in") or []).lower()
        for p in plan["person_captures"]
    )
    thumbs = thumbnail_concepts_with_identity("Meta Muse", "Meta Muse Code", ents)
    assert len(thumbs) >= 5
    assert "required_assets" in thumbs[0]
    assert "Chloe" in thumbs[0]["visual_description"]


def test_extract_bytedance_entities():
    ents = extract_entities(
        "ByteDance 10 trillion parameter model",
        "TikTok parent company AI foundation model",
    )
    assert any(e["company"] == "ByteDance" for e in ents)
    plan = build_identity_capture_plan("ByteDance 10T", ents, [])
    assert any("ByteDance" in (l.get("company") or "") for l in plan["logo_captures"])


def test_meta_facts_have_phase_numbers():
    facts = _facts_from_grounding(
        {"brief_overview": "meta public nuisance new mexico"},
        "Meta public nuisance",
    )
    text = " ".join(f["fact"] for f in facts)
    assert "375" in text or "567" in text


def test_cinematic_library_for_ai_topics():
    prompts = cinematic_for_topic("China 10 trillion parameter AI model")
    assert len(prompts) >= 3
    assert any("Chloe" in p for p in prompts)


def test_motion_recipes_glass_panels():
    r = motion_graphic_recipes([{"fact": "$567M", "source": "BBC", "when": "hook"}])
    assert r[0]["type"] == "kinetic_stat"
    steps = " ".join(r[0].get("capcut_steps") or [])
    assert "glass" in steps.lower()
    assert "Chloe" in steps


def test_studio_layout_spatial_rules():
    m = studio_layout_manifest()
    assert m["anchor"] == "Chloe"
    assert m["channel_badge"] == "AIInfoRoom"
    assert m["panel_slots"]
    assert panel_for_asset("kinetic_stat")["slot"]
    card = article_card_prompt("10 TRILLION PARAMETERS", "The Verge", "ByteDance")
    assert "glass" in card.lower()
    assert "ByteDance" in card


def test_studio_reference_plates_exist():
    paths = studio_reference_paths()
    assert paths["base"].exists()
    assert paths["logo_panel"].exists()
    manifest = studio_reference_manifest()
    assert manifest["files"]["base"]["exists"]
    assert "chloe_studio_base.jpg" in manifest["files"]["base"]["relative"]
