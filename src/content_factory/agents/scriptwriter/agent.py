"""Scriptwriter — tight hybrid storytelling (MKBHD + Mrwhosetheboss + AI Revolution).

Anti-bloat: Elements of Style, one thesis, no section rehash.
Completeness: retries + min floors without padding to 12–16 min by default.
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

# id, title, goal, target_words, start_ts, end_ts, min_words, max_words
SECTION_PLAN: list[tuple[str, str, str, int, str, str, int, int]] = [
    (
        "hook",
        "Hook",
        "AI-Rev cold open: one concrete claim or tension only — no channel intro, no scene fluff",
        70,
        "00:00",
        "00:20",
        35,
        95,
    ),
    (
        "why_it_matters",
        "Why It Matters",
        "Arun stakes: human/market cause-chain — money, power, delay, jobs, who wins",
        160,
        "00:20",
        "01:40",
        80,
        230,
    ),
    (
        "explanation",
        "How It Works",
        "How it works ONCE in plain language — do not restate the hook claim as an opener",
        200,
        "01:40",
        "03:30",
        100,
        290,
    ),
    (
        "benchmarks_demos",
        "Benchmarks & Evidence",
        "Pay off the cold open with numbers, comparisons, sources — new info only",
        180,
        "03:30",
        "05:20",
        90,
        270,
    ),
    (
        "implications",
        "Implications",
        "Second-order effects — advance the chain; never rehash earlier sections",
        160,
        "05:20",
        "06:50",
        80,
        230,
    ),
    (
        "bigger_picture",
        "Bigger Picture",
        "Race/timeline/arc in one tight beat — not a second essay",
        140,
        "06:50",
        "08:10",
        70,
        210,
    ),
    (
        "cta",
        "Close & CTA",
        "One-line recap max + open-loop question + soft CTA — no hard sell",
        70,
        "08:10",
        "08:50",
        35,
        100,
    ),
]

MIN_TOTAL_WORDS = 700
TARGET_TOTAL_WORDS = (900, 1600)
HARD_MAX_WORDS = 1800
SECTION_LLM_RETRIES = 3

NATURAL_VOICE_RULES = """
NATURAL SPOKEN VOICE (critical — this is read aloud by TTS):
- Sound like a sharp human host talking to a smart friend — NOT like ChatGPT, NOT like a press release.
- Write like a high-quality Financial Times / curiosity article read aloud:
  clear narrative arc, concrete details, earned conclusions — not bullet-list AI sludge.
- Excited but analytical. Conversational. Use contractions (it's, that's, we're, don't).
- Short and medium sentences. Vary rhythm. One idea per breath.
- ALWAYS put spaces between words and after punctuation. Never glue words.
- For numbers and units, write for speech: "ten trillion", "two point eight trillion",
  "ninety percent", "one hundred fifty meters per hour".
- Ban AI tells: delve, tapestry, landscape, game-changer, unlock the power, in today's world,
  without further ado, let's dive in, as an AI, in conclusion, it is important to note,
  picture this, picture a, the kicker, tantalizing, in short, without a doubt.
- No stacked hype adjectives. Prefer concrete detail over vague superlatives.
- Soft CTA only at the end — never hard sell.

ELEMENTS OF STYLE (Strunk & White — non-negotiable):
- Omit needless words. Every sentence must earn its place.
- Active voice. Definite, specific, concrete language.
- Do NOT re-explain a claim already paid off in a prior section.
- Do NOT open every section with the same cold-open image or thesis dump.
- Prefer one strong example over three weak restatements.
- Put the emphatic idea at the end of the sentence when it lands harder.

HYBRID STORYTELLING (AIInfoRoom peers):
- AI Revolution: cold open is the claim; kinetic proof; race stakes.
- Mrwhosetheboss: human/market cause-chain; friend energy; economics of who gets squeezed.
- MKBHD: one point of the video; trust via under-claiming; experience/evidence before verdict.
"""

SYSTEM_ONESHOT = f"""You are the Scriptwriter Agent for AIInfoRoom (tech YouTube).

{NATURAL_VOICE_RULES}

Structure as a TIGHT spoken piece (~900–1600 words, ~7–12 minutes at 150 wpm).
Do NOT pad to 12–16 minutes. Prefer cutting fluff over adding filler.

Sections:
1) hook — cold open claim only
2) why_it_matters — stakes / cause-chain
3) explanation — how once
4) benchmarks_demos — numbers + sources
5) implications — second-order only
6) bigger_picture — race/arc once
7) cta — open loop + soft CTA

Return JSON VideoScript with sections array.
Do not invent hard facts not supported by the research brief.
"""

SYSTEM_SECTION = f"""You are the Scriptwriter Agent writing ONE section of a AIInfoRoom script.
{NATURAL_VOICE_RULES}

Return JSON only:
{{
  "narration": "spoken narration for THIS section only — tight, complete, no truncation",
  "visual_cues": ["..."],
  "on_screen_text": ["..."],
  "source_callouts": ["..."]
}}

CRITICAL:
- Stay near target_words. Do not exceed max_words.
- Do not restate previous_sections_summary. Advance the story.
- Soft CTA only if section_id is cta.
- No invented stats.
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
    if n.rstrip().endswith("...") and _word_count(n) < min_words * 1.5:
        return True
    return False


def _looks_bloated(narration: str, max_words: int) -> bool:
    return _word_count(narration) > max_words


def _trim_to_max(narration: str, max_words: int) -> str:
    words = (narration or "").split()
    if len(words) <= max_words:
        return narration
    # Prefer ending on a sentence boundary near the cap
    cut = " ".join(words[:max_words])
    for sep in (". ", "! ", "? "):
        idx = cut.rfind(sep)
        if idx > len(cut) * 0.5:
            return normalize_spoken_text(cut[: idx + 1])
    return normalize_spoken_text(cut.rstrip(",;:") + ".")


def _expand_brief_section(
    brief: ResearchBrief,
    sid: str,
    title: str,
    channel: str,
    target_words: int,
) -> str:
    """Tight prose from research — no pad loops that rehash the same overview."""
    overview = (brief.overview or "").strip()
    technical = (brief.technical_details or "").strip()
    benchmarks = (brief.benchmarks or "").strip()
    implications = (brief.implications or "").strip()
    historical = (brief.historical_context or "").strip()
    claims = brief.key_claims or []
    claim_line = str(claims[0]) if claims else brief.topic_title

    pieces = {
        "hook": (
            f"{claim_line}. "
            f"{overview[:280] if overview else brief.topic_title}. "
            f"Here's the breakdown."
        ),
        "why_it_matters": (
            f"Here's why it hits. {implications or overview}".strip()[:900]
        ),
        "explanation": (technical or overview)[:1100],
        "benchmarks_demos": (
            benchmarks
            or (
                f"What we can verify: {'; '.join(str(c) for c in claims[:4])}."
                if claims
                else overview[:700]
            )
        ),
        "implications": (implications or overview)[:900],
        "bigger_picture": (historical or overview)[:800],
        "cta": (
            f"Bottom line on {brief.topic_title}: watch the sources, not the hype. "
            f"If you want more deep dives like this from {channel}, subscribe and tell us "
            f"what we should cover next."
        ),
    }
    text = pieces.get(sid, overview or claim_line)
    # Light expand only if severely short — one pass, no cycling the same blob
    if _word_count(text) < max(int(target_words * 0.55), 30):
        extra = {
            "hook": claim_line,
            "why_it_matters": overview[:400],
            "explanation": overview[:300],
            "benchmarks_demos": " ".join(str(c) for c in claims[:3]),
            "implications": historical[:300],
            "bigger_picture": implications[:300],
            "cta": "",
        }.get(sid, "")
        if extra and extra not in text:
            text = f"{text} {extra}".strip()
    if sid != "cta" and text and not text.rstrip().endswith((".", "!", "?")):
        text = text.rstrip() + "."
    return normalize_spoken_text(text)


def _heuristic_script(brief: ResearchBrief, channel: str) -> VideoScript:
    sections: list[ScriptSection] = []
    for sid, title, _goal, target_words, start_ts, end_ts, _min_w, max_w in SECTION_PLAN:
        narration = _trim_to_max(
            _expand_brief_section(brief, sid, title, channel, target_words),
            max_w,
        )
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
    max_words: int,
    start_ts: str,
    end_ts: str,
    prior_summaries: list[str],
) -> tuple[ScriptSection, dict[str, Any]]:
    meta: dict[str, Any] = {
        "section_id": sid,
        "attempts": 0,
        "used_fallback": False,
        "word_count": 0,
        "trimmed": False,
    }
    storytelling = style.get("storytelling") or {}
    user_base = {
        "channel": channel,
        "tone": style.get("tone"),
        "storytelling": storytelling,
        "section_id": sid,
        "section_title": title,
        "section_goal": goal,
        "target_words": target_words,
        "min_words": min_words,
        "max_words": max_words,
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
        "previous_sections_summary": prior_summaries[-4:],
        "instruction": (
            f"Write about {target_words} words (min {min_words}, hard max {max_words}). "
            f"Advance past previous sections. Omit needless words. No rehash."
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
                if best_narration and _looks_bloated(best_narration, max_words):
                    user["retry_reason"] = (
                        f"Previous attempt was bloated ({_word_count(best_narration)} words). "
                        f"Cut to under {max_words}. Omit needless words. No restatement."
                    )
                else:
                    user["retry_reason"] = (
                        f"Previous attempt was incomplete ({_word_count(best_narration)} words). "
                        f"Hit at least {min_words} with NEW information only."
                    )
            data = chat_json(
                SYSTEM_SECTION,
                json.dumps(user, ensure_ascii=False, default=str),
                settings=settings,
                temperature=0.4 + 0.05 * (attempt - 1),
                max_tokens=2048,
            )
            narration = normalize_spoken_text((data.get("narration") or "").strip())
            if not narration:
                raise LLMError(f"Empty narration for section {sid}")
            if _looks_bloated(narration, max_words):
                narration = _trim_to_max(narration, max_words)
                meta["trimmed"] = True
            # Prefer complete non-bloated over long incomplete
            if not _looks_incomplete(narration, min_words):
                best_narration = narration
                best_data = data
                break
            if _word_count(narration) > _word_count(best_narration):
                best_narration = narration
                best_data = data
            log.warning(
                "Section %s attempt %s incomplete (%s words, min %s)",
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
            "Section %s fallback (last_err=%s, best_words=%s)",
            sid,
            last_err,
            _word_count(best_narration),
        )
        meta["used_fallback"] = True
        expanded = _expand_brief_section(brief, sid, title, channel, target_words)
        if best_narration and _word_count(best_narration) >= 30:
            narration = normalize_spoken_text(f"{best_narration} {expanded}")
        else:
            narration = expanded
        narration = _trim_to_max(narration, max_words)
        visual_cues = list(best_data.get("visual_cues") or []) or [
            f"Chloe studio · {title} glass panels"
        ]
        on_screen = list(best_data.get("on_screen_text") or [])
        sources = list(best_data.get("source_callouts") or [])
    else:
        narration = best_narration
        if _looks_bloated(narration, max_words):
            narration = _trim_to_max(narration, max_words)
            meta["trimmed"] = True
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
    sections: list[ScriptSection] = []
    prior_summaries: list[str] = []
    quality: list[dict[str, Any]] = []

    for (
        sid,
        title,
        goal,
        target_words,
        start_ts,
        end_ts,
        min_words,
        max_words,
    ) in SECTION_PLAN:
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
            max_words=max_words,
            start_ts=start_ts,
            end_ts=end_ts,
            prior_summaries=prior_summaries,
        )
        sections.append(sec)
        quality.append(meta)
        prior_summaries.append(f"{title}: {sec.narration[:240]}")

    soft = sections[-1].narration if sections else ""
    script = VideoScript(
        title_working=brief.topic_title,
        topic_title=brief.topic_title,
        sections=sections,
        soft_cta=soft,
    ).recompute_stats()

    # Only expand if below floor AND incomplete — never pad good tight scripts
    if script.word_count < MIN_TOTAL_WORDS:
        log.warning(
            "Script total %s words < %s; light expand of thin sections only",
            script.word_count,
            MIN_TOTAL_WORDS,
        )
        fixed: list[ScriptSection] = []
        for sec in sections:
            plan = next((p for p in SECTION_PLAN if p[0] == sec.id), None)
            min_w = plan[6] if plan else 50
            max_w = plan[7] if plan else 250
            target = plan[3] if plan else 120
            if sec.id != "cta" and _looks_incomplete(sec.narration, min_w):
                extra = _expand_brief_section(brief, sec.id, sec.title, channel, target)
                merged = _trim_to_max(
                    normalize_spoken_text(f"{sec.narration} {extra}"), max_w
                )
                fixed.append(sec.model_copy(update={"narration": merged}))
            else:
                fixed.append(sec)
        sections = fixed
        script = VideoScript(
            title_working=brief.topic_title,
            topic_title=brief.topic_title,
            sections=sections,
            soft_cta=sections[-1].narration if sections else "",
        ).recompute_stats()

    if script.word_count > HARD_MAX_WORDS:
        log.warning(
            "Script over hard max (%s > %s); trimming longest body sections",
            script.word_count,
            HARD_MAX_WORDS,
        )
        trimmed: list[ScriptSection] = []
        for sec in sections:
            plan = next((p for p in SECTION_PLAN if p[0] == sec.id), None)
            max_w = plan[7] if plan else 200
            if sec.id not in {"hook", "cta"} and _word_count(sec.narration) > max_w * 0.9:
                trimmed.append(
                    sec.model_copy(
                        update={"narration": _trim_to_max(sec.narration, int(max_w * 0.85))}
                    )
                )
            else:
                trimmed.append(sec)
        sections = trimmed
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
            "hard_max_words": HARD_MAX_WORDS,
            "complete_sections": [p[0] for p in SECTION_PLAN],
            "no_truncation": True,
            "no_padding": True,
        },
    }
    data = chat_json(
        SYSTEM_ONESHOT,
        json.dumps(user, ensure_ascii=False, default=str),
        settings=settings,
        temperature=0.5,
        max_tokens=6144,
    )
    script = VideoScript.model_validate(data)
    fixed = []
    for sec in script.sections:
        plan = next((p for p in SECTION_PLAN if p[0] == sec.id), None)
        max_w = plan[7] if plan else 250
        narr = normalize_spoken_text(sec.narration)
        if _looks_bloated(narr, max_w):
            narr = _trim_to_max(narr, max_w)
        fixed.append(sec.model_copy(update={"narration": narr}))
    script = script.model_copy(update={"sections": fixed}).recompute_stats()

    if script.word_count < MIN_TOTAL_WORDS * 0.6 or len(script.sections) < 5:
        log.warning(
            "Oneshot incomplete (words=%s sections=%s); heuristic base",
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
                    log.info(
                        "Scriptwriter chunked generation (tight hybrid spine, anti-bloat)"
                    )
                    script, quality_log = _chunked_script(
                        brief, channel, ctx.style, ctx.settings
                    )
                else:
                    script = _oneshot_script(brief, ctx.style, ctx.settings, channel)
            except (LLMError, Exception) as exc:  # noqa: BLE001
                log.warning("LLM scriptwriter failed (%s); heuristic script", exc)
                script = _heuristic_script(brief, channel)
                quality_log = [{"error": str(exc), "used_fallback": "full_heuristic"}]
        else:
            script = _heuristic_script(brief, channel)
            quality_log = [{"used_fallback": "llm_disabled"}]

        # Only merge heuristic if still broken stubs — not to hit old 1400 floors
        if script.word_count < MIN_TOTAL_WORDS * 0.5:
            log.warning(
                "Final script very short (%s); merging thin sections from heuristic",
                script.word_count,
            )
            heur = _heuristic_script(brief, channel)
            heur_by_id = {s.id: s for s in heur.sections}
            merged_secs: list[ScriptSection] = []
            for sec in script.sections:
                plan = next((p for p in SECTION_PLAN if p[0] == sec.id), None)
                min_w = plan[6] if plan else 40
                max_w = plan[7] if plan else 250
                if _looks_incomplete(sec.narration, min_w) and sec.id in heur_by_id:
                    h = heur_by_id[sec.id]
                    merged_secs.append(
                        sec.model_copy(
                            update={
                                "narration": _trim_to_max(
                                    normalize_spoken_text(
                                        f"{sec.narration} {h.narration}".strip()
                                    ),
                                    max_w,
                                )
                            }
                        )
                    )
                else:
                    merged_secs.append(sec)
            have = {s.id for s in merged_secs}
            for row in SECTION_PLAN:
                if row[0] not in have and row[0] in heur_by_id:
                    merged_secs.append(heur_by_id[row[0]])
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
                "hard_max_words": HARD_MAX_WORDS,
                "storytelling": "hybrid_mkbhd_arun_airevolution",
                "section_quality": quality_log,
                "meets_floor": script.word_count >= MIN_TOTAL_WORDS,
                "under_hard_max": script.word_count <= HARD_MAX_WORDS,
            },
        )

        log.info(
            "Script ready: words=%s runtime≈%s min floor=%s hard_max_ok=%s",
            script.word_count,
            script.estimated_runtime_minutes,
            script.word_count >= MIN_TOTAL_WORDS,
            script.word_count <= HARD_MAX_WORDS,
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
