"""Scriptwriter — high-retention 12–16 minute video scripts (chunked for free/local models)."""

from __future__ import annotations

import json
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import ResearchBrief, ScriptSection, VideoScript
from content_factory.state import PipelineState
from content_factory.tools.llm import chat_json, LLMError
from content_factory.tools.speech_text import normalize_spoken_text
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

SECTION_PLAN = [
    ("hook", "Hook", "15-30 second cold open", 250, "00:00", "00:25"),
    ("why_it_matters", "Why It Matters", "stakes and audience impact", 350, "00:25", "02:30"),
    ("explanation", "How It Works", "clear technical explanation", 550, "02:30", "07:00"),
    ("benchmarks_demos", "Benchmarks & Evidence", "numbers, demos, evidence", 400, "07:00", "10:00"),
    ("implications", "Implications", "business, geo, industry, society", 350, "10:00", "12:30"),
    ("bigger_picture", "Bigger Picture", "history and larger arc", 300, "12:30", "14:30"),
    ("cta", "Close & CTA", "soft CTA only", 150, "14:30", "15:30"),
]

NATURAL_VOICE_RULES = """
NATURAL SPOKEN VOICE (critical — this is read aloud by TTS):
- Sound like a sharp human host talking to a smart friend — NOT like ChatGPT, NOT like a press release.
- Excited but analytical. Conversational. Use contractions (it's, that's, we're, don't).
- Short and medium sentences. Vary rhythm. One idea per breath.
- ALWAYS put spaces between words and after punctuation. Never glue words (bad: "end.Start", "300Wh/kg").
- For numbers and units, write for speech clarity: "three hundred watt-hours per kilogram", "twenty to thirty percent", "five hundred sixty-seven million dollars".
- Ban AI tells: delve, tapestry, landscape, game-changer, unlock the power, in today's world, without further ado, let's dive in, as an AI.
- No stacked hype adjectives. Prefer concrete detail over vague superlatives.
- Rhetorical questions and brief asides are good if they feel human.
- Soft CTA only at the end — never hard sell.
"""

SYSTEM_ONESHOT = f"""You are the Scriptwriter Agent for a tech YouTube channel.

Channel voice: Excited but analytical, clear, authoritative, accessible — and unmistakably human.
{NATURAL_VOICE_RULES}

Structure EVERY script as:
1) hook (15–30 seconds) — powerful cold open, no long intro
2) why_it_matters
3) explanation
4) benchmarks_demos
5) implications
6) bigger_picture
7) cta — SOFT CTA only

Target: 12–16 minutes spoken (~1800–2400 words at ~150 wpm).
Include timestamps, visual_cues, on_screen_text, source_callouts.

Return JSON VideoScript with sections array.
Do not invent hard facts not supported by the research brief.
"""

SYSTEM_SECTION = f"""You are the Scriptwriter Agent writing ONE section of a tech YouTube script.
{NATURAL_VOICE_RULES}

Return JSON only:
{{
  "narration": "full spoken narration for this section only — ready to read aloud",
  "visual_cues": ["..."],
  "on_screen_text": ["..."],
  "source_callouts": ["..."]
}}
No invented stats. Soft CTA only if this is the cta section.
The narration field must be speakable prose with clear word spacing and natural pauses (periods, commas).
"""


def script_to_markdown(script: VideoScript) -> str:
    lines = [
        f"# Script: {script.title_working}\n",
        f"**Topic:** {script.topic_title}  ",
        f"**Est. runtime:** {script.estimated_runtime_minutes} min  ",
        f"**Word count:** {script.word_count}\n",
        "---\n",
    ]
    for sec in script.sections:
        lines.append(
            f"## [{sec.start_timestamp}–{sec.end_timestamp}] {sec.title} (`{sec.id}`)\n"
        )
        lines.append(sec.narration)
        if sec.visual_cues:
            lines.append("\n**Visual cues:**")
            for v in sec.visual_cues:
                lines.append(f"- {v}")
        if sec.on_screen_text:
            lines.append("\n**On-screen text:**")
            for t in sec.on_screen_text:
                lines.append(f"- {t}")
        if sec.source_callouts:
            lines.append("\n**Sources on screen:**")
            for s in sec.source_callouts:
                lines.append(f"- {s}")
        lines.append("\n---\n")
    if script.soft_cta:
        lines.append(f"\n**Soft CTA:** {script.soft_cta}\n")
    return "\n".join(lines)


def _heuristic_script(brief: ResearchBrief, channel: str) -> VideoScript:
    hook = (
        f"What if everything you thought about {brief.topic_title} just changed? "
        f"Here's what actually happened — and why it matters right now."
    )
    sections = [
        ScriptSection(
            id="hook",
            title="Hook",
            start_timestamp="00:00",
            end_timestamp="00:25",
            narration=hook,
            visual_cues=["Cold open montage related to topic"],
            on_screen_text=[brief.topic_title],
        ),
        ScriptSection(
            id="why_it_matters",
            title="Why It Matters",
            start_timestamp="00:25",
            end_timestamp="02:00",
            narration=brief.implications or brief.overview,
            visual_cues=["Stakeholder graphics", "map/industry icons"],
        ),
        ScriptSection(
            id="explanation",
            title="How It Works",
            start_timestamp="02:00",
            end_timestamp="07:00",
            narration=brief.technical_details or brief.overview,
            visual_cues=["Diagram explainer", "simple animation"],
            source_callouts=[c.title for c in brief.citations[:3]],
        ),
        ScriptSection(
            id="benchmarks_demos",
            title="Benchmarks & Evidence",
            start_timestamp="07:00",
            end_timestamp="10:00",
            narration=brief.benchmarks
            or "Independent benchmarks are still emerging — here's what we can verify.",
            visual_cues=["Chart overlays"],
            source_callouts=[c.title for c in brief.citations[3:6]],
        ),
        ScriptSection(
            id="implications",
            title="Implications",
            start_timestamp="10:00",
            end_timestamp="12:30",
            narration=brief.implications or brief.overview,
            visual_cues=["Industry reaction B-roll"],
        ),
        ScriptSection(
            id="bigger_picture",
            title="Bigger Picture",
            start_timestamp="12:30",
            end_timestamp="14:00",
            narration=brief.historical_context or brief.overview,
            visual_cues=["Timeline graphic"],
        ),
        ScriptSection(
            id="cta",
            title="Close & CTA",
            start_timestamp="14:00",
            end_timestamp="14:45",
            narration=(
                f"That's the state of {brief.topic_title}. If you want more deep dives like this from "
                f"{channel}, subscribe and tell us what breakthrough we should cover next."
            ),
            visual_cues=["End screen placeholders"],
        ),
    ]
    script = VideoScript(
        title_working=brief.topic_title,
        topic_title=brief.topic_title,
        sections=sections,
        soft_cta=sections[-1].narration,
    )
    return script.recompute_stats()


def _chunked_script(
    brief: ResearchBrief,
    channel: str,
    style: dict[str, Any],
    settings: Any,
) -> VideoScript:
    """Write section-by-section — critical for small local models."""
    sections: list[ScriptSection] = []
    prior_summaries: list[str] = []

    for sid, title, goal, target_words, start_ts, end_ts in SECTION_PLAN:
        user = {
            "channel": channel,
            "tone": style.get("tone"),
            "section_id": sid,
            "section_title": title,
            "section_goal": goal,
            "target_words": target_words,
            "topic_title": brief.topic_title,
            "research_brief": {
                "overview": brief.overview,
                "technical_details": brief.technical_details[:2000],
                "benchmarks": brief.benchmarks[:1200],
                "implications": brief.implications[:1200],
                "historical_context": brief.historical_context[:800],
                "key_claims": brief.key_claims[:8],
                "citations": [c.model_dump() for c in brief.citations[:8]],
                "uncertainty_flags": brief.uncertainty_flags[:5],
            },
            "previous_sections_summary": prior_summaries[-3:],
        }
        try:
            data = chat_json(
                SYSTEM_SECTION,
                json.dumps(user, ensure_ascii=False, default=str),
                settings=settings,
                temperature=0.5,
                max_tokens=2048,
            )
            narration = normalize_spoken_text((data.get("narration") or "").strip())
            if not narration:
                raise LLMError(f"Empty narration for section {sid}")
            sec = ScriptSection(
                id=sid,
                title=title,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                narration=narration,
                visual_cues=list(data.get("visual_cues") or []),
                on_screen_text=list(data.get("on_screen_text") or []),
                source_callouts=list(data.get("source_callouts") or []),
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Chunked section %s failed (%s); heuristic fill", sid, exc)
            fallback = _heuristic_script(brief, channel)
            matching = next((s for s in fallback.sections if s.id == sid), None)
            sec = matching or ScriptSection(
                id=sid,
                title=title,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                narration=brief.overview[:500],
            )
        sections.append(sec)
        prior_summaries.append(f"{title}: {sec.narration[:200]}")

    soft = sections[-1].narration if sections else ""
    script = VideoScript(
        title_working=brief.topic_title,
        topic_title=brief.topic_title,
        sections=sections,
        soft_cta=soft,
    )
    return script.recompute_stats()


def _oneshot_script(
    brief: ResearchBrief,
    style: dict[str, Any],
    settings: Any,
) -> VideoScript:
    user = {
        "channel_style": style,
        "research_brief": brief.model_dump(mode="json"),
    }
    data = chat_json(
        SYSTEM_ONESHOT,
        json.dumps(user, ensure_ascii=False, default=str),
        settings=settings,
        temperature=0.55,
        max_tokens=8192,
    )
    script = VideoScript.model_validate(data)
    # Normalize every section for TTS-safe spacing and anti-AI tells
    fixed = []
    for sec in script.sections:
        fixed.append(
            sec.model_copy(update={"narration": normalize_spoken_text(sec.narration)})
        )
    return script.model_copy(update={"sections": fixed}).recompute_stats()


def run_scriptwriter(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "scriptwriter"
    try:
        raw = state.get("research_brief")
        if not raw:
            return mark_failed(stage, "No research_brief in state")
        brief = ResearchBrief.model_validate(raw)
        channel = ctx.style.get("channel_name") or ctx.settings.channel_name

        if ctx.use_llm:
            try:
                # Free/local small models: chunk by default
                use_chunked = bool(ctx.settings.chunked_script)
                provider = (ctx.settings.llm_provider or "auto").lower()
                if (
                    provider in {"ollama", "ollama_cloud", "free"}
                    or ctx.settings.active_profile == "free"
                ):
                    use_chunked = True
                if use_chunked:
                    log.info("Scriptwriter using chunked generation (free/local-friendly)")
                    script = _chunked_script(brief, channel, ctx.style, ctx.settings)
                else:
                    script = _oneshot_script(brief, ctx.style, ctx.settings)
            except (LLMError, Exception) as exc:  # noqa: BLE001
                log.warning("LLM scriptwriter failed (%s); heuristic script", exc)
                script = _heuristic_script(brief, channel)
        else:
            script = _heuristic_script(brief, channel)

        ctx.store.write_json("script/draft.json", script)
        ctx.store.write_text("script/draft.md", script_to_markdown(script))
        ctx.store.write_text("script/narration.txt", script.full_narration)

        return mark_done(
            stage,
            {
                "script_draft": script.model_dump(mode="json"),
                "script_final": script.model_dump(mode="json"),
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Scriptwriter failed")
        return mark_failed(stage, str(exc))
