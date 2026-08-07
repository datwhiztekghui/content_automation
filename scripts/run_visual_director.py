"""Run Visual Director only on an existing run folder."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from config.settings import Settings, set_active_settings  # noqa: E402
from content_factory.agents.visual_director import run_visual_director  # noqa: E402
from content_factory.state import initial_state  # noqa: E402
from content_factory.models.schemas import PipelineMode, StageName  # noqa: E402


def main(run_id: str) -> None:
    run = ROOT / "data" / "runs" / run_id
    script_path = run / "script" / "final.json"
    if not script_path.exists():
        script_path = run / "script" / "draft.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))

    settings = Settings().apply_profile("free")
    set_active_settings(settings)
    try:
        state = initial_state(
            run_id=run_id,
            mode=PipelineMode.MEDIA,
            enabled_stages=[StageName.VISUAL_DIRECTOR],
            dry_run_media=True,
            auto_approve=True,
            headless=True,
        )
        state["script_final"] = script
        state["script_draft"] = script
        # Force ArtifactStore path via run_id + settings.runs_dir
        result = run_visual_director(state)
        print(json.dumps({k: result.get(k) for k in ("stage_status", "messages", "errors")}, indent=2))
        vp = result.get("visual_package") or {}
        print(
            f"shots={len(vp.get('shot_list') or [])} "
            f"prompts={len(vp.get('broll_prompts') or [])} "
            f"thumbs={len(vp.get('thumbnail_concepts') or [])}"
        )
        print(f"wrote under {run / 'visuals'}")
    finally:
        set_active_settings(None)


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "20260807T134022Z_6494630c"
    main(rid)
