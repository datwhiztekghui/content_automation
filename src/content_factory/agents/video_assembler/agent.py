"""Video Assembler — edit bible + asset manifest for CapCut/Descript."""

from __future__ import annotations

from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import AssemblyPackage, VideoScript
from content_factory.state import PipelineState
from content_factory.utils.logging import get_logger

log = get_logger(__name__)


def run_video_assembler(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "video_assembler"
    try:
        raw = state.get("script_final") or state.get("script_draft")
        if not raw:
            return mark_failed(stage, "No script for assembly")
        script = VideoScript.model_validate(raw)
        voice = state.get("voice_package") or {}
        visual = state.get("visual_package") or {}

        manifest: list[dict[str, Any]] = [
            {
                "id": "narration",
                "type": "audio",
                "path": voice.get("narration_text_path") or "voice/narration_full.txt",
                "notes": "Generate VO via ElevenLabs if audio_paths empty",
            },
            {"id": "script", "type": "document", "path": "script/final.md"},
            {"id": "visuals", "type": "document", "path": "visuals/package.md"},
        ]
        for i, shot in enumerate(visual.get("shot_list") or []):
            manifest.append(
                {
                    "id": f"shot_{i}",
                    "type": "broll_or_graphic",
                    "section_id": shot.get("section_id"),
                    "description": shot.get("description"),
                }
            )

        timeline = []
        for sec in script.sections:
            timeline.append(
                f"{sec.start_timestamp}-{sec.end_timestamp} | {sec.id} | VO + "
                f"{', '.join(sec.visual_cues[:2]) if sec.visual_cues else 'A-roll'}"
            )

        bible = f"""# Edit Bible — {script.title_working}

## Overview
- Target runtime: {script.estimated_runtime_minutes} min
- Word count: {script.word_count}
- Editors: CapCut / Descript / Premiere

## Import checklist
1. Import narration audio (or generate from `voice/narration_full.txt`)
2. Place VO on A1; ripple trim to markers
3. Lay B-roll / AI gen clips from shot list under VO
4. Add lower-thirds and source callouts from script
5. Color grade tech-documentary (cool shadows, clean highlights)
6. Loudness normalize to -14 LUFS
7. Export 4K or 1080p 30/60fps H.264

## Timeline
""" + "\n".join(f"- {t}" for t in timeline)

        package = AssemblyPackage(
            edit_bible_markdown=bible,
            asset_manifest=manifest,
            timeline_notes=timeline,
        )
        ctx.store.write_json("assembly/package.json", package)
        ctx.store.write_text("assembly/EDIT_BIBLE.md", bible)
        ctx.store.write_json("assembly/asset_manifest.json", manifest)
        return mark_done(stage, {"assembly_package": package.model_dump(mode="json")})
    except Exception as exc:  # noqa: BLE001
        log.exception("Video Assembler failed")
        return mark_failed(stage, str(exc))
