"""SEO & Packaging — titles, description, tags, Shorts hooks."""

from __future__ import annotations

import json
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import SEOPackage, VideoScript
from content_factory.state import PipelineState
from content_factory.tools.llm import chat_json
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

SYSTEM = """You are the SEO & Packaging Agent for a tech YouTube channel.
Create optimized packaging that is accurate (no false clickbait).
Return JSON:
{
  "titles": ["5-8 title options"],
  "description": "full YT description with timestamps/chapters embedded",
  "chapters": [{"time": "0:00", "label": "..."}],
  "tags": ["..."],
  "end_screen": {"elements": ["subscribe", "related_video", "playlist"]},
  "shorts_hooks": [{"hook": "...", "caption": "...", "platform": "youtube_shorts|tiktok|reels"}]
}
Provide 5-8 Shorts/Reels hook ideas.
"""


def _heuristic_seo(script: VideoScript, channel: str) -> SEOPackage:
    chapters = [
        {"time": sec.start_timestamp.lstrip("0") if sec.start_timestamp != "00:00" else "0:00",
         "label": sec.title}
        for sec in script.sections
    ]
    # normalize 00:25 -> 0:25 style-ish
    chapter_lines = "\n".join(f"{c['time']} {c['label']}" for c in chapters)
    desc = f"""{script.title_working}

{script.sections[0].narration[:280] if script.sections else ''}...

📌 Chapters
{chapter_lines}

Sources cited in the research brief for this episode.
Subscribe to {channel} for more breakthrough explainers.

#tech #ai #science #robotics
"""
    return SEOPackage(
        titles=[
            script.title_working,
            f"{script.topic_title} Explained",
            f"Why {script.topic_title} Matters Right Now",
            f"The Truth About {script.topic_title}",
            f"{script.topic_title}: What Nobody Is Saying",
        ],
        description=desc.strip(),
        chapters=chapters,
        tags=[
            "technology",
            "AI",
            "robotics",
            "science",
            "tech news",
            script.topic_title[:50],
            channel,
        ],
        end_screen={"elements": ["subscribe", "related_video", "playlist"]},
        shorts_hooks=[
            {
                "hook": script.sections[0].narration[:120] if script.sections else script.topic_title,
                "caption": f"{script.topic_title} — full video on channel",
                "platform": "youtube_shorts",
            },
            {
                "hook": f"Stop scrolling. {script.topic_title} just changed the game.",
                "caption": "Full breakdown in bio / long-form",
                "platform": "tiktok",
            },
            {
                "hook": "Three things the headlines missed:",
                "caption": f"{script.topic_title} explained",
                "platform": "reels",
            },
        ],
    )


def run_seo_packaging(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "seo_packaging"
    try:
        raw = state.get("script_final") or state.get("script_draft")
        if not raw:
            return mark_failed(stage, "No script for SEO")
        script = VideoScript.model_validate(raw)
        channel = ctx.style.get("channel_name") or ctx.settings.channel_name
        package = _heuristic_seo(script, channel)

        if ctx.use_llm:
            try:
                data = chat_json(
                    SYSTEM,
                    json.dumps(
                        {
                            "channel": channel,
                            "script": script.model_dump(mode="json"),
                        },
                        default=str,
                    ),
                    settings=ctx.settings,
                    temperature=0.5,
                )
                package = SEOPackage.model_validate(data)
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM SEO failed (%s); heuristic package", exc)

        ctx.store.write_json("seo/package.json", package)
        ctx.store.write_text(
            "seo/description.txt",
            package.description,
        )
        ctx.store.write_text(
            "seo/titles.txt",
            "\n".join(f"- {t}" for t in package.titles),
        )
        return mark_done(stage, {"seo_package": package.model_dump(mode="json")})
    except Exception as exc:  # noqa: BLE001
        log.exception("SEO packaging failed")
        return mark_failed(stage, str(exc))
