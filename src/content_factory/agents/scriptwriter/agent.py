"""Scriptwriter — full complete 12–16 min scripts (FT-style curiosity + channel voice).

Hardens against empty LLM JSON and silent short heuristics: per-section retries,
minimum word floors, and explicit quality flags when fallback is used.
"""

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

# id, title, goal, target_words, start_ts, end_ts, min_words (floor after retries)
SECTION_PLAN: list[tuple[str, str, str, int, str, str, int]] = [
    ("hook", "Hook", "15-30 second cold open with a concrete claim or tension", 250, "00:00", "00:25", 80),
    ("why_it_matters", "Why It Matters", "stakes and audience impact — curiosity, not lecture", 350, "00:25", "02:30", 180),
    ("explanation", "How It Works", "clear technical explanation in plain language", 550, "02:30", "07:00", 280),
    ("benchmarks_demos", "Benchmarks & Evidence", "numbers, demos, evidence with sources", 400, "07:00", "10:00", 200),
    ("implications", "Implications", "business, geo, industry, society", 350, "10:00", "12:30", 180),
    ("bigger_picture", "Bigger Picture", "history and larger arc — complete the story", 300, "12:30", "14:30", 150),
    ("cta", "Close & CTA", "soft CTA only — no hard sell", 150, "14:30", "15:30", 60),
]

# Whole-script floors (reject silent short dumps)
MIN_TOTAL_WORDS = 1400
TARGET_TOTAL_WORDS = (1800, 2400)
SECTION_LLM_RETRIES = 3

NATURAL_VOICE_RULES = """
NATURAL SPOKEN VOICE (critical — this is read aloud by TTS):
- Sound like a sharp human host talking to a smart friend — NOT like ChatGPT, NOT like a press release.
- Write like a high-quality Financial Times / long-form curiosity article read aloud:
  clear narrative arc, concrete details, earned conclusions — not bullet-list AI sludge.
- Excited but analytical. Conversational. Use contractions (it's, that's, we're, don't).
- Short and medium sentences. Vary rhythm. One idea per breath.
- ALWAYS put spaces between words and after punctuation. Never glue words (bad: "end.Start", "300Wh/kg").
- For numbers and units, write for speech clarity: "three hundred watt-hours per kilogram",
  "twenty to thirty percent", "five hundred sixty-seven million dollars".
- Ban AI tells: delve, tapestry, landscape, game-changer, unlock the power, in today's world,
  without further ado, let's dive in, as an AI, in conclusion, it is important to note.
- No stacked hype adjectives. Prefer concrete detail over vague superlatives.
- Rhetorical questions and brief asides are good if they feel human.
- Soft CTA only at the end — never hard sell.
- COMPLETE every section: no trailing "..." , no "more on this later" without payoff,
  no empty placeholders, no "insert research here".
"""

SYSTEM_ONESHOT = f"""You are the Scriptwriter Agent for Tech Frontier (tech YouTube).

Channel voice: Excited but analytical, clear, authoritative, accessible — unmistakably human.
{NATURAL_VOICE_RULES}

Structure EVERY script as a COMPLETE article-length spoken piece:
1) hook (15–30 seconds) — powerful cold open, no long intro
2) why_it_matters
3) explanation
4) benchmarks_demos
5) implications
6) bigger_picture
7) cta — SOFT CTA only

Target: 12–16 minutes spoken (~1800–2400 words at ~150 wpm).
Include timestamps, visual_cues, on_screen_text, source_callouts.
Every section must be full prose suitable for TTS — never truncated mid-thought.

Return JSON VideoScript with sections array.
Do not invent hard facts not supported by the research brief.
"""

SYSTEM_SECTION = f"""You are the Scriptwriter Agent writing ONE COMPLETE section of a tech YouTube script.
{NATURAL_VOICE_RULES}

Return JSON only:
{{
  "narration": "full spoken narration for this section only — ready to read aloud, COMPLETE, no truncation",
  "visual_cues": ["..."],
  "on_screen_text": ["..."],
  "source_callouts": ["..."]
}}
No invented stats. Soft CTA only if this is the cta section.
The narration field must be speakable prose with clear word spacing and natural pauses.
Hit the target_words closely. Never return empty narration or a one-sentence stub when
target_words is hundreds of words. Finish thoughts cleanly.
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


def _word_count(text: str) -> int:
    return len((text or "").split())


def _looks_incomplete(narration: str, min_words: int) -> bool:
    n = (narration or "").strip()
    if not n:
        return True
    if _word_count(n) < min_words:
        return True
    low = n.lower()
    stubs = (
        "todo",
        "tbd",
        "insert research",
        "placeholder",
        "[narration]",
        "lorem ipsum",
        "write the rest",
        "to be continued",
    )
    if any(s in low for s in stubs):
        return True
    # Abrupt ellipsis-only ending without substance
    if n.rstrip().endswith("...") and _word_count(n) < min_words * 1.5:
        return True
    return False


def _expand_brief_section(
    brief: ResearchBrief,
    sid: str,
    title: str,
    channel: str,
    target_words: int,
) -> str:
    """Deterministic prose expansion from research — never silent empty stub."""
    overview = (brief.overview or "").strip()
    technical = (brief.technical_details or "").strip()
    benchmarks = (brief.benchmarks or "").strip()
    implications = (brief.implications or "").strip()
    historical = (brief.historical_context or "").strip()
    claims = brief.key_claims or []
    claim_blob = " ".join(str(c) for c in claims[:6])

    openers = {
        "hook": (
            f"What if the story around {brief.topic_title} is bigger than the headline? "
            f"Here's what actually happened — and why it matters right now."
        ),
        "why_it_matters": (
            f"So why should you care about {brief.topic_title}? "
            f"Because the stakes hit how products get built, who holds power, and what comes next."
        ),
        "explanation": (
            f"Let's break down how {brief.topic_title} actually works — without the buzzwords."
        ),
        "benchmarks_demos": (
            f"Claims are cheap. Evidence is not. Here's what we can verify on {brief.topic_title}."
        ),
        "implications": (
            f"Zoom out. What does {brief.topic_title} change for industry, competitors, and you?"
        ),
        "bigger_picture": (
            f"This didn't appear from nowhere. Here's the longer arc around {brief.topic_title}."
        ),
        "cta": (
            f"That's the state of {brief.topic_title}. If you want more deep dives like this from "
            f"{channel}, subscribe and tell us what breakthrough we should cover next."
        ),
    }
    body_map = {
        "hook": f"{overview} {claim_blob}".strip(),
        "why_it_matters": f"{implications or overview} {claim_blob}".strip(),
        "explanation": f"{technical or overview}".strip(),
        "benchmarks_demos": (
            benchmarks
            or (
                "Independent benchmarks are still emerging — here's what public sources support. "
                f"{claim_blob}"
            )
        ).strip(),
        "implications": f"{implications or overview}".strip(),
        "bigger_picture": f"{historical or overview}".strip(),
        "cta": openers["cta"],
    }
    opener = openers.get(sid, overview)
    body = body_map.get(sid, overview)
    # Expand by cycling research sentences until near target (still plain prose)
    parts = [opener, body]
    filler_pool = [
        overview,
        technical,
        implications,
        historical,
        claim_blob,
        f"We'll stay honest about uncertainty: {'; '.join(brief.uncertainty_flags[:3])}."
        if brief.uncertainty_flags
        else f"Where sources disagree, we flag it — {channel} prefers under-claiming.",
    ]
    text = " ".join(p for p in parts if p)
    idx = 0
    while _word_count(text) < max(target_words * 0.7, 40) and idx < 12:
        chunk = filler_pool[idx % len(filler_pool)]
        if chunk and chunk not in text[-500:]:
            text = f"{text} {chunk}".strip()
        idx += 1
    # Soft close for non-CTA sections
    if sid != "cta" and not text.rstrip().endswith((".", "!", "?")):
        text = text.rstrip() + "."
    return normalize_spoken_text(text)


def _heuristic_script(brief: ResearchBrief, channel: str) -> VideoScript:
    sections: list[ScriptSection] = []
    for sid, title, _goal, target_words, start_ts, end_ts, _min_w in SECTION_PLAN:
        narration = _expand_brief_section(brief, sid, title, channel, target_words)
        sections.append(
            ScriptSection(
                id=sid,
                title=title,
                start_timestamp=start_ts,
                end_timestamp=end_ts,
                narration=narration,
                visual_cues=[
                    f"Chloe virtual studio · glass panel for {title}",
                    "Real logos/portraits when named",
                ],
                on_screen_text=[brief.topic_title[:60]] if sid == "hook" else [],
                source_callouts=[c.title for c in brief.citations[:2]]
                if sid in {"explanation", "benchmarks_demos"}
                else [],
            )
        )
    script = VideoScript(
        title_working=brief.topic_title,
        topic_title=brief.topic_title,
        sections=sections,
        soft_cta=sections[-1].narration if sections else "",
    )
    return script.recompute_stats()


def _generate_section_narration(
    *,
    brief: ResearchBrief,
    channel: str,
    style: dict[str, Any],
    settings: Any,
    sid: str,
    title: str,
    goal: str,
    target_words: int,
    min_words: int,
    start_ts: str,
    end_ts: str,
    prior_summaries: list[str],
) -> tuple[ScriptSection, dict[str, Any]]:
    """LLM section with retries; falls back to expanded brief prose if still weak."""
    meta: dict[str, Any] = {
        "section_id": sid,
        "attempts": 0,
        "used_fallback": False,
        "word_count": 0,
    }
    user_base = {
        "channel": channel,
        "tone": style.get("tone"),
        "section_id": sid,
        "section_title": title,
        "section_goal": goal,
        "target_words": target_words,
        "min_words": min_words,
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
        "instruction": (
            f"Write a COMPLETE section of about {target_words} words "
            f"(absolute minimum {min_words}). Full prose, natural speech, finished thoughts."
        ),
    }

    best_narration = ""
    best_data: dict[str, Any] = {}
    last_err: Exception | None = None

    for attempt in range(1, SECTION_LLM_RETRIES + 1):
        meta["attempts"] = attempt
        try:
            user = dict(user_base)
            if attempt > 1:
                user["retry_reason"] = (
                    f"Previous attempt was too short or incomplete "
                    f"({_word_count(best_narration)} words). "
                    f"Expand to at least {min_words} words with full spoken paragraphs."
                )
            data = chat_json(
                SYSTEM_SECTION,
                json.dumps(user, ensure_ascii=False, default=str),
                settings=settings,
                temperature=0.45 + 0.05 * (attempt - 1),
                max_tokens=3072,
            )
            narration = normalize_spoken_text((data.get("narration") or "").strip())
            if not narration:
                raise LLMError(f"Empty narration for section {sid}")
            if _word_count(narration) > _word_count(best_narration):
                best_narration = narration
                best_data = data
            if not _looks_incomplete(narration, min_words):
                best_narration = narration
                best_data = data
                break
            log.warning(
                "Section %s attempt %s under floor (%s words < %s); retrying",
                sid,
                attempt,
                _word_count(narration),
                min_words,
            )
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            log.warning("Chunked section %s attempt %s failed (%s)", sid, attempt, exc)

    if _looks_incomplete(best_narration, min_words):
        log.warning(
            "Section %s using expanded brief fallback (last_err=%s, best_words=%s)",
            sid,
            last_err,
            _word_count(best_narration),
        )
        meta["used_fallback"] = True
        # Prefer best LLM fragment prepended to expansion if partial value
        expanded = _expand_brief_section(brief, sid, title, channel, target_words)
        if best_narration and _word_count(best_narration) >= 40:
            narration = normalize_spoken_text(f"{best_narration} {expanded}")
        else:
            narration = expanded
        visual_cues = list(best_data.get("visual_cues") or []) or [
            f"Chloe studio · {title} glass panels"
        ]
        on_screen = list(best_data.get("on_screen_text") or [])
        sources = list(best_data.get("source_callouts") or [])
    else:
        narration = best_narration
        visual_cues = list(best_data.get("visual_cues") or [])
        on_screen = list(best_data.get("on_screen_text") or [])
        sources = list(best_data.get("source_callouts") or [])

    meta["word_count"] = _word_count(narration)
    sec = ScriptSection(
        id=sid,
        title=title,
        start_timestamp=start_ts,
        end_timestamp=end_ts,
        narration=narration,
        visual_cues=visual_cues,
        on_screen_text=on_screen,
        source_callouts=sources,
    )
    return sec, meta


def _chunked_script(
    brief: ResearchBrief,
    channel: str,
    style: dict[str, Any],
    settings: Any,
) -> tuple[VideoScript, list[dict[str, Any]]]:
    """Write section-by-section with completion guards — critical for free/local models."""
    sections: list[ScriptSection] = []
    prior_summaries: list[str] = []
    quality: list[dict[str, Any]] = []

    for sid, title, goal, target_words, start_ts, end_ts, min_words in SECTION_PLAN:
        sec, meta = _generate_section_narration(
            brief=brief,
            channel=channel,
            style=style,
            settings=settings,
            sid=sid,
            title=title,
            goal=goal,
            target_words=target_words,
            min_words=min_words,
            start_ts=start_ts,
            end_ts=end_ts,
            prior_summaries=prior_summaries,
        )
        sections.append(sec)
        quality.append(meta)
        prior_summaries.append(f"{title}: {sec.narration[:200]}")

    soft = sections[-1].narration if sections else ""
    script = VideoScript(
        title_working=brief.topic_title,
        topic_title=brief.topic_title,
        sections=sections,
        soft_cta=soft,
    ).recompute_stats()

    # Whole-script floor: expand weakest body sections if still short
    if script.word_count < MIN_TOTAL_WORDS:
        log.warning(
            "Script total %s words < %s; expanding body sections from brief",
            script.word_count,
            MIN_TOTAL_WORDS,
        )
        fixed: list[ScriptSection] = []
        for sec in sections:
            plan = next((p for p in SECTION_PLAN if p[0] == sec.id), None)
            min_w = plan[6] if plan else 100
            target = plan[3] if plan else 300
            if sec.id != "cta" and _word_count(sec.narration) < target * 0.75:
                extra = _expand_brief_section(
                    brief, sec.id, sec.title, channel, target
                )
                merged = normalize_spoken_text(f"{sec.narration} {extra}")
                fixed.append(sec.model_copy(update={"narration": merged}))
                quality.append(
                    {
                        "section_id": sec.id,
                        "post_expand": True,
                        "word_count": _word_count(merged),
                    }
                )
            else:
                fixed.append(sec)
        sections = fixed
        script = VideoScript(
            title_working=brief.topic_title,
            topic_title=brief.topic_title,
            sections=sections,
            soft_cta=sections[-1].narration if sections else "",
        ).recompute_stats()

    return script, quality


def _oneshot_script(
    brief: ResearchBrief,
    style: dict[str, Any],
    settings: Any,
    channel: str,
) -> VideoScript:
    user = {
        "channel_style": style,
        "research_brief": brief.model_dump(mode="json"),
        "requirements": {
            "min_total_words": MIN_TOTAL_WORDS,
            "target_words": TARGET_TOTAL_WORDS,
            "complete_sections": [p[0] for p in SECTION_PLAN],
            "no_truncation": True,
        },
    }
    data = chat_json(
        SYSTEM_ONESHOT,
        json.dumps(user, ensure_ascii=False, default=str),
        settings=settings,
        temperature=0.55,
        max_tokens=8192,
    )
    script = VideoScript.model_validate(data)
    fixed = []
    for sec in script.sections:
        fixed.append(
            sec.model_copy(update={"narration": normalize_spoken_text(sec.narration)})
        )
    script = script.model_copy(update={"sections": fixed}).recompute_stats()

    # Reject weak oneshot: fall back to chunked path would be ideal; expand if short
    if script.word_count < MIN_TOTAL_WORDS or len(script.sections) < 5:
        log.warning(
            "Oneshot script incomplete (words=%s sections=%s); using heuristic expansion base",
            script.word_count,
            len(script.sections),
        )
        return _heuristic_script(brief, channel)
    return script


def run_scriptwriter(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "scriptwriter"
    try:
        raw = state.get("research_brief")
        if not raw:
            return mark_failed(stage, "No research_brief in state")
        brief = ResearchBrief.model_validate(raw)
        channel = ctx.style.get("channel_name") or ctx.settings.channel_name
        quality_log: list[dict[str, Any]] = []

        if ctx.use_llm:
            try:
                use_chunked = bool(ctx.settings.chunked_script)
                provider = (ctx.settings.llm_provider or "auto").lower()
                if (
                    provider in {"ollama", "ollama_cloud", "free"}
                    or ctx.settings.active_profile == "free"
                ):
                    use_chunked = True
                if use_chunked:
                    log.info("Scriptwriter using chunked generation (free/local-friendly)")
                    script, quality_log = _chunked_script(
                        brief, channel, ctx.style, ctx.settings
                    )
                else:
                    script = _oneshot_script(brief, ctx.style, ctx.settings, channel)
            except (LLMError, Exception) as exc:  # noqa: BLE001
                log.warning("LLM scriptwriter failed (%s); expanded heuristic script", exc)
                script = _heuristic_script(brief, channel)
                quality_log = [{"error": str(exc), "used_fallback": "full_heuristic"}]
        else:
            script = _heuristic_script(brief, channel)
            quality_log = [{"used_fallback": "llm_disabled"}]

        if script.word_count < MIN_TOTAL_WORDS:
            log.warning(
                "Final script still short (%s < %s words) — expanded heuristic pass",
                script.word_count,
                MIN_TOTAL_WORDS,
            )
            # Merge heuristic expansion without wiping good LLM sections
            heur = _heuristic_script(brief, channel)
            merged_secs: list[ScriptSection] = []
            heur_by_id = {s.id: s for s in heur.sections}
            for sec in script.sections:
                plan = next((p for p in SECTION_PLAN if p[0] == sec.id), None)
                min_w = plan[6] if plan else 80
                if _looks_incomplete(sec.narration, min_w) and sec.id in heur_by_id:
                    h = heur_by_id[sec.id]
                    merged_secs.append(
                        sec.model_copy(
                            update={
                                "narration": normalize_spoken_text(
                                    f"{sec.narration} {h.narration}".strip()
                                )
                            }
                        )
                    )
                else:
                    merged_secs.append(sec)
            # Ensure all plan sections exist
            have = {s.id for s in merged_secs}
            for sid, title, _g, _t, start_ts, end_ts, _m in SECTION_PLAN:
                if sid not in have and sid in heur_by_id:
                    merged_secs.append(heur_by_id[sid])
            order = {p[0]: i for i, p in enumerate(SECTION_PLAN)}
            merged_secs.sort(key=lambda s: order.get(s.id, 99))
            script = VideoScript(
                title_working=script.title_working or brief.topic_title,
                topic_title=brief.topic_title,
                sections=merged_secs,
                soft_cta=merged_secs[-1].narration if merged_secs else "",
            ).recompute_stats()

        ctx.store.write_json("script/draft.json", script)
        ctx.store.write_text("script/draft.md", script_to_markdown(script))
        ctx.store.write_text("script/narration.txt", script.full_narration)
        ctx.store.write_json(
            "script/quality.json",
            {
                "word_count": script.word_count,
                "estimated_runtime_minutes": script.estimated_runtime_minutes,
                "min_total_words": MIN_TOTAL_WORDS,
                "target_words": list(TARGET_TOTAL_WORDS),
                "section_quality": quality_log,
                "meets_floor": script.word_count >= MIN_TOTAL_WORDS,
            },
        )

        log.info(
            "Script ready: words=%s runtime≈%s min meets_floor=%s",
            script.word_count,
            script.estimated_runtime_minutes,
            script.word_count >= MIN_TOTAL_WORDS,
        )

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
