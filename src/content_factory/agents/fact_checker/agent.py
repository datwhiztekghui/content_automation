"""Fact-Checker & Editor — accuracy, flow, retention, voice, policy."""

from __future__ import annotations

import json
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.agents.scriptwriter.agent import script_to_markdown
from content_factory.models.schemas import ChangeLogEntry, ResearchBrief, VideoScript
from content_factory.state import PipelineState
from content_factory.tools.llm import chat_json, LLMError
from content_factory.tools.speech_text import normalize_spoken_text
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

SYSTEM_PROMPT = """You are the Fact-Checker & Editor Agent for a tech YouTube channel.

Review the draft script against the research brief for:
1) factual accuracy (no unsupported claims)
2) logical flow
3) retention risks (slow middle, weak hook, buried lede)
4) brand voice (excited but analytical; clear; authoritative; accessible)
5) policy issues (defamation, medical/financial overclaim, etc.)
6) NATURAL SPEECH polish for voiceover:
   - Remove AI-sounding phrases (delve, tapestry, game-changer, unlock the power, let's dive in, in today's world)
   - Prefer contractions and varied sentence length
   - Ensure spaces between words and after punctuation (TTS must not glue words)
   - Make numbers/units speakable ("twenty percent", "five hundred sixty-seven million dollars")
   - Keep it human — like a real presenter, not a model summary

Return JSON:
{
  "script": { ... full VideoScript object with revisions applied ... },
  "changelog": [
    {
      "category": "accuracy|flow|retention|voice|policy",
      "severity": "info|warning|critical",
      "original": "...",
      "revised": "...",
      "rationale": "..."
    }
  ]
}

If the draft is already strong, return it with minor polish and a short changelog.
Prefer under-claiming over inventing facts. Soft CTA must remain soft.
Always return fully speakable narration text.
"""


def run_fact_checker(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "fact_checker"
    try:
        raw_script = state.get("script_draft")
        raw_brief = state.get("research_brief")
        if not raw_script:
            return mark_failed(stage, "No script_draft in state")
        script = VideoScript.model_validate(raw_script)
        brief = ResearchBrief.model_validate(raw_brief) if raw_brief else None

        changelog: list[ChangeLogEntry] = []
        final = script

        if ctx.use_llm and brief is not None:
            try:
                user = {
                    "channel_style": ctx.style,
                    "research_brief": brief.model_dump(mode="json"),
                    "script_draft": script.model_dump(mode="json"),
                }
                data = chat_json(
                    SYSTEM_PROMPT,
                    json.dumps(user, ensure_ascii=False, default=str),
                    settings=ctx.settings,
                    temperature=0.3,
                    max_tokens=8192,
                )
                final = VideoScript.model_validate(data["script"])
                final_sections = [
                    s.model_copy(
                        update={"narration": normalize_spoken_text(s.narration)}
                    )
                    for s in final.sections
                ]
                final = final.model_copy(update={"sections": final_sections}).recompute_stats()
                changelog = [
                    ChangeLogEntry.model_validate(c)
                    for c in data.get("changelog", [])
                ]
            except (LLMError, Exception) as exc:  # noqa: BLE001
                log.warning("LLM fact-check failed (%s); pass-through draft", exc)
                changelog = [
                    ChangeLogEntry(
                        category="accuracy",
                        severity="warning",
                        rationale=f"Automated fact-check skipped: {exc}. Draft passed through for human review.",
                    )
                ]
        else:
            changelog = [
                ChangeLogEntry(
                    category="accuracy",
                    severity="info",
                    rationale="No LLM and/or no brief — draft passed through. Human review required.",
                )
            ]

        # Always normalize speakable text (even on pass-through / failed LLM edit)
        final = final.model_copy(
            update={
                "sections": [
                    s.model_copy(
                        update={"narration": normalize_spoken_text(s.narration)}
                    )
                    for s in final.sections
                ]
            }
        ).recompute_stats()

        ctx.store.write_json("script/final.json", final)
        ctx.store.write_text("script/final.md", script_to_markdown(final))
        ctx.store.write_json(
            "script/changelog.json",
            [c.model_dump(mode="json") for c in changelog],
        )
        ctx.store.write_text("script/narration.txt", final.full_narration)

        return mark_done(
            stage,
            {
                "script_final": final.model_dump(mode="json"),
                "edit_changelog": [c.model_dump(mode="json") for c in changelog],
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Fact-checker failed")
        return mark_failed(stage, str(exc))
