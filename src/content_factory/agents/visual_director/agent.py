"""Visual Director — shot lists, B-roll prompts, thumbnails."""

from __future__ import annotations

import json
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import ThumbnailConcept, VideoScript, VisualPackage
from content_factory.state import PipelineState
from content_factory.tools.llm import chat_json
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

SYSTEM = """You are the Visual Director for a tech YouTube channel.
From the script, produce:
- shot_list: ordered shots with section_id, description, duration_hint, type (a-roll/b-roll/graphic)
- broll_prompts: prompts optimized for Kling / Runway / Grok Imagine / stock search keywords
- lower_thirds: nameplates / labels
- thumbnail_concepts: 3-5 high-converting concepts with headline + text_overlay + visual_description

Return JSON matching VisualPackage fields.
"""


def _heuristic_visuals(script: VideoScript) -> VisualPackage:
    shots = []
    broll = []
    for sec in script.sections:
        shots.append(
            {
                "section_id": sec.id,
                "description": sec.visual_cues[0] if sec.visual_cues else sec.title,
                "duration_hint": f"{sec.start_timestamp}-{sec.end_timestamp}",
                "type": "b-roll" if sec.id != "hook" else "cold-open",
            }
        )
        broll.append(
            {
                "section_id": sec.id,
                "provider_hints": ["kling", "runway", "grok_imagine", "stock"],
                "prompt": f"Cinematic tech documentary B-roll for: {sec.title}. {script.topic_title}",
                "stock_keywords": [script.topic_title, sec.id, "technology"],
            }
        )
    thumbs = [
        ThumbnailConcept(
            concept_id="t1",
            headline=script.title_working[:60],
            subtext="What just changed",
            visual_description="Bold subject on dark gradient, shocked face cutout optional",
            text_overlay=script.title_working.split(":")[0][:40],
            emotion="curiosity",
        ),
        ThumbnailConcept(
            concept_id="t2",
            headline="This changes everything",
            subtext=script.topic_title[:40],
            visual_description="Before/after split of old vs new tech",
            text_overlay="GAME CHANGER?",
            emotion="urgency",
        ),
        ThumbnailConcept(
            concept_id="t3",
            headline="The real story",
            subtext="Not what headlines say",
            visual_description="Document + chip/robot macro shot",
            text_overlay="EXPLAINED",
            emotion="authority",
        ),
    ]
    return VisualPackage(
        shot_list=shots,
        broll_prompts=broll,
        lower_thirds=[
            {"text": script.topic_title, "when": "why_it_matters"},
            {"text": "Key benchmark", "when": "benchmarks_demos"},
        ],
        thumbnail_concepts=thumbs,
    )


def run_visual_director(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "visual_director"
    try:
        raw = state.get("script_final") or state.get("script_draft")
        if not raw:
            return mark_failed(stage, "No script for visuals")
        script = VideoScript.model_validate(raw)

        package = _heuristic_visuals(script)
        if ctx.use_llm:
            try:
                data = chat_json(
                    SYSTEM,
                    json.dumps({"script": script.model_dump(mode="json")}),
                    settings=ctx.settings,
                    temperature=0.5,
                )
                package = VisualPackage.model_validate(data)
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM visuals failed (%s); heuristic package", exc)

        ctx.store.write_json("visuals/package.json", package)
        lines = ["# Visual Package\n", "## Shot List\n"]
        for s in package.shot_list:
            lines.append(f"- [{s.get('section_id')}] {s.get('description')}")
        lines.append("\n## Thumbnail Concepts\n")
        for t in package.thumbnail_concepts:
            lines.append(f"### {t.concept_id}: {t.headline}")
            lines.append(f"{t.visual_description}\nOverlay: `{t.text_overlay}`\n")
        ctx.store.write_text("visuals/package.md", "\n".join(lines))

        return mark_done(stage, {"visual_package": package.model_dump(mode="json")})
    except Exception as exc:  # noqa: BLE001
        log.exception("Visual Director failed")
        return mark_failed(stage, str(exc))
