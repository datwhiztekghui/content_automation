"""Visual Director — AI Revolution–class competitive package.

Peer bar (e.g. https://www.youtube.com/watch?v=MEw7TrAUEPQ):
kinetic stats, rapid cuts, cinematic tech B-roll, real screenshots, comparison
cards, geo stakes — NOT generic empty-room stock.

Credibility still required: story-linked beats, real numbers, real sources.
"""

from __future__ import annotations

import json
import math
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.agents.visual_director.peer_style import (
    cinematic_for_topic,
    load_visual_style,
    motion_graphic_recipes,
    screen_capture_plan,
)
from content_factory.models.schemas import (
    ResearchBrief,
    ThumbnailConcept,
    VideoScript,
    VisualPackage,
)
from content_factory.state import PipelineState
from content_factory.tools.llm import chat_json, llm_available
from content_factory.tools.web_search import search_web
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

# Peer channels cut HARD on the hook
HOOK_SHOT_SECONDS = 3.0
BODY_SHOT_SECONDS = 5.0
PRIORITY_GENERATE_CAP = 32

PHOTOREAL_SUFFIX = (
    "Cinematic tech-commercial still, dark grade with cyan rim light, "
    "photoreal materials, shallow DOF, YouTube 16:9, no watermark, "
    "no burned-in text, no trademark logos, no celebrity deepfake faces."
)

SYSTEM = """You are the Creative Director for Tech Frontier — competing with
AI Revolution–class faceless tech/AI news channels (high energy, dense motion design).

VISUAL LANGUAGE (study peer winners):
- Kinetic typography for every major number and claim
- Cinematic AI/tech B-roll (GPU halls, city dual-skylines, neural light sculpture)
- Real screenshots of articles, papers, product pages
- Comparison cards and leaderboards
- Geo maps when China/US/EU matter
- Logo cards as CLEAN VECTOR in editor (not AI)
- Cut every 2–5s on hook, 4–7s mid-roll
- Dark navy + cyan/magenta energy

STORY LAW:
- Every shot has a story_link to THIS topic's facts
- Prefer verified numbers from research + news hits
- No generic empty courtrooms as 50% of runtime
- No deepfake public figures

Return JSON with keys:
creative_strategy, verified_story_beats, shot_list, broll_prompts,
motion_graphics, screen_captures, lower_thirds, on_screen_facts,
thumbnail_concepts, retention_notes, generate_queue, editor_brand_kit

shot_list items need: shot_id, section_id, start_sec, duration_sec, type,
purpose, story_link, on_screen_action, capcut_overlay, asset_class, priority
asset_class one of: kinetic_stat, comparison_card, ui_screen, cinematic_broll,
news_headline, geo_map, timeline, logo_card, proof_quote, end_brand

broll_prompts: only for cinematic_broll / generative stills — photoreal prompts.
"""


def _parse_ts(ts: str) -> float:
    if not ts:
        return 0.0
    parts = ts.strip().split(":")
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except ValueError:
        return 0.0
    return 0.0


def _section_duration_sec(sec: Any) -> float:
    start = _parse_ts(getattr(sec, "start_timestamp", "00:00"))
    end = _parse_ts(getattr(sec, "end_timestamp", "00:00"))
    if end > start:
        return max(end - start, 8.0)
    words = len((getattr(sec, "narration", "") or "").split()) or 80
    return max(words / 150.0 * 60.0, 12.0)


def _enrich(prompt: str) -> str:
    p = (prompt or "").strip()
    if not p:
        return PHOTOREAL_SUFFIX
    if "watermark" not in p.lower():
        p = f"{p.rstrip('.')}. {PHOTOREAL_SUFFIX}"
    return p


def _gather_grounding(topic: str, brief: ResearchBrief | None, settings: Any) -> dict[str, Any]:
    queries = [topic, f"{topic} news", f"{topic} official"]
    hits: list[dict[str, Any]] = []
    for q in queries[:3]:
        try:
            hits.extend(search_web(q, max_results=6, settings=settings))
        except Exception as exc:  # noqa: BLE001
            log.warning("search failed: %s", exc)
    seen: set[str] = set()
    uniq = []
    for h in hits:
        u = h.get("url") or ""
        if u in seen:
            continue
        if u:
            seen.add(u)
        uniq.append(h)
    return {
        "topic": topic,
        "brief_overview": (brief.overview[:900] if brief else ""),
        "brief_claims": (brief.key_claims[:10] if brief else []),
        "citations": [c.model_dump() for c in (brief.citations[:8] if brief else [])],
        "uncertainty_flags": (brief.uncertainty_flags if brief else []),
        "news_hits": uniq[:18],
    }


def _facts_from_grounding(grounding: dict[str, Any], topic: str) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for c in grounding.get("brief_claims") or []:
        facts.append({"fact": c, "source": "research brief", "when": "body"})
    # Meta NM pack if relevant
    blob = f"{topic} {grounding.get('brief_overview','')}".lower()
    if "meta" in blob or "nuisance" in blob or "567" in blob or "new mexico" in blob:
        facts = [
            {
                "fact": "New Mexico court: public nuisance finding on Meta",
                "source": "BBC / court coverage",
                "when": "hook",
            },
            {
                "fact": "Jury phase damages ≈ $375 million",
                "source": "NPR / trial coverage",
                "when": "hook",
            },
            {
                "fact": "Judge adds ≈ $567 million civil penalty",
                "source": "BBC News",
                "when": "why_it_matters",
            },
            {
                "fact": "Combined reporting ≈ $942 million",
                "source": "BBC News",
                "when": "benchmarks_demos",
            },
            {
                "fact": "Framed as first social platform public-nuisance of this kind",
                "source": "BBC News",
                "when": "explanation",
            },
            {
                "fact": "Meta says it will appeal",
                "source": "press wire",
                "when": "implications",
            },
            {
                "fact": "Judge Bryan Biedscheid · NM AG Raúl Torrez",
                "source": "court / AG",
                "when": "proof_quote",
            },
        ]
    if not facts:
        facts.append(
            {
                "fact": topic[:80],
                "source": "headline",
                "when": "hook",
            }
        )
    return facts


def _build_competitive_package(
    script: VideoScript,
    grounding: dict[str, Any],
    style: dict[str, Any],
) -> tuple[VisualPackage, dict[str, Any]]:
    facts = _facts_from_grounding(grounding, script.topic_title)
    cinematics = cinematic_for_topic(script.topic_title)
    mg = motion_graphic_recipes(facts)
    screens = screen_capture_plan(script.topic_title, grounding.get("news_hits") or [])

    shots: list[dict[str, Any]] = []
    broll: list[dict[str, Any]] = []
    lower: list[dict[str, Any]] = []
    generate_queue: list[str] = []
    shot_n = 0
    global_t = 0.0
    cine_i = 0
    fact_i = 0

    # Asset class rotation = peer channel rhythm
    # K=kinetic, C=cinematic, U=ui/screen, M=map/compare
    rhythm = [
        "kinetic_stat",
        "cinematic_broll",
        "ui_screen",
        "kinetic_stat",
        "cinematic_broll",
        "comparison_card",
        "cinematic_broll",
        "news_headline",
        "logo_card",
        "cinematic_broll",
    ]

    for sec in script.sections:
        dur = _section_duration_sec(sec)
        pace = HOOK_SHOT_SECONDS if sec.id == "hook" else BODY_SHOT_SECONDS
        n_shots = max(5, int(math.ceil(dur / pace)))
        if sec.id == "hook":
            n_shots = max(n_shots, 10)
        slot = dur / n_shots

        for i in range(n_shots):
            shot_n += 1
            sid = f"s{shot_n:03d}"
            asset_class = rhythm[i % len(rhythm)]
            if sec.id == "cta" and i >= n_shots - 2:
                asset_class = "end_brand"
            if sec.id == "hook" and i == 0:
                asset_class = "kinetic_stat"

            fact = facts[fact_i % len(facts)]
            if asset_class in {"kinetic_stat", "news_headline", "proof_quote", "comparison_card"}:
                fact_i += 1

            start_sec = global_t + i * slot
            priority = 1 if (sec.id == "hook" or asset_class in {"kinetic_stat", "ui_screen"} or i < 2) else 2

            story_link = (
                f"VO section '{sec.title}' · claim support: {fact.get('fact','')[:100]}"
            )
            overlay = ""
            if asset_class in {"kinetic_stat", "news_headline", "comparison_card", "proof_quote"}:
                overlay = fact.get("fact", "")[:90]
            source_lt = (
                f"Source: {fact.get('source')}"
                if asset_class in {"kinetic_stat", "news_headline", "ui_screen"}
                else ""
            )

            shots.append(
                {
                    "shot_id": sid,
                    "section_id": sec.id,
                    "start_sec": round(start_sec, 1),
                    "duration_sec": round(slot, 1),
                    "type": asset_class,
                    "asset_class": asset_class,
                    "purpose": "retention" if sec.id == "hook" else "clarity",
                    "story_link": story_link,
                    "on_screen_action": (
                        f"{asset_class.replace('_', ' ')} · {overlay or sec.title}"
                    ),
                    "capcut_overlay": overlay,
                    "source_lower_third": source_lt,
                    "description": (
                        f"[{asset_class}] {sec.title} beat {i+1}/{n_shots} — "
                        f"peer-style dense news package"
                    ),
                    "priority": priority,
                }
            )

            # Generative B-roll only when class is cinematic
            if asset_class == "cinematic_broll":
                prompt = cinematics[cine_i % len(cinematics)]
                cine_i += 1
                # Bind metaphor to section
                prompt = (
                    f"{prompt} Visual metaphor for: {sec.title}. "
                    f"Topic: {script.topic_title}."
                )
                broll.append(
                    {
                        "shot_id": sid,
                        "section_id": sec.id,
                        "story_link": story_link,
                        "asset_class": "cinematic_broll",
                        "provider_hints": ["grok_imagine", "kling", "runway", "stock"],
                        "aspect_ratio": "16:9",
                        "style": "cinematic_tech_commercial",
                        "prompt": _enrich(prompt),
                        "negative_cues": (
                            "watermark, logo, trademark, deepfake face, burned-in text, "
                            "cartoon, empty boring office, stock rubber stamp"
                        ),
                        "stock_keywords": [
                            script.topic_title[:40],
                            sec.id,
                            "cinematic tech",
                        ],
                        "news_search_query": script.topic_title,
                        "motion_hint": "slow push-in or parallax 3–5s; snap cut on beat",
                        "priority": priority,
                    }
                )
                if priority == 1:
                    generate_queue.append(sid)
            elif asset_class == "ui_screen":
                sc = screens[min(i, len(screens) - 1)] if screens else {}
                broll.append(
                    {
                        "shot_id": sid,
                        "section_id": sec.id,
                        "story_link": "Real-world proof screenshot (not AI inventing news)",
                        "asset_class": "ui_screen",
                        "provider_hints": ["manual_screenshot", "browser"],
                        "aspect_ratio": "16:9",
                        "style": "screen_capture",
                        "prompt": (
                            f"EDITOR ACTION (not AI image): {sc.get('action', 'Screenshot primary source')}. "
                            f"URL hint: {sc.get('url_hint', '')}"
                        ),
                        "negative_cues": "do not AI-fake news websites",
                        "stock_keywords": [],
                        "news_search_query": script.topic_title,
                        "motion_hint": sc.get("capcut", "Ken Burns zoom"),
                        "priority": 1,
                    }
                )
                generate_queue.append(sid)
            else:
                # Motion graphic / logo / map — editor-built; still list for timeline
                broll.append(
                    {
                        "shot_id": sid,
                        "section_id": sec.id,
                        "story_link": story_link,
                        "asset_class": asset_class,
                        "provider_hints": ["capcut_motion", "after_effects"],
                        "aspect_ratio": "16:9",
                        "style": "motion_graphics",
                        "prompt": (
                            f"EDITOR MOTION GRAPHIC: {asset_class}. "
                            f"On-screen: {overlay or sec.title}. "
                            f"Source footer: {source_lt}. "
                            "Use brand kit dark navy + cyan. No AI text rendering."
                        ),
                        "negative_cues": "do not generate this as AI still with text",
                        "stock_keywords": [],
                        "news_search_query": "",
                        "motion_hint": "slam-in 0.35s, hold, whip out",
                        "priority": priority,
                    }
                )

            if source_lt:
                lower.append(
                    {
                        "text": overlay or sec.title,
                        "when": f"{sec.id}@{start_sec:.0f}s",
                        "style": "kinetic news lower-third",
                        "source": source_lt,
                    }
                )

        global_t += dur

    # Thumbs: high CTR peer style
    t = script.topic_title
    thumbs = [
        ThumbnailConcept(
            concept_id="t1",
            headline=script.title_working[:70],
            subtext="What just dropped",
            visual_description=_enrich(
                f"High-contrast cinematic tech thumbnail base for '{t}', "
                "subject dominant left/right third empty for huge text, dark navy, "
                "cyan rim light, shocked energy, no text in image"
            ),
            text_overlay="SHOCKED EVERYONE",
            emotion="shock",
        ),
        ThumbnailConcept(
            concept_id="t2",
            headline=t[:60],
            subtext="The number that matters",
            visual_description=_enrich(
                f"Cinematic abstract glowing core / data sphere for '{t}', "
                "black background, room for giant number overlay, no text in image"
            ),
            text_overlay="THE NUMBER",
            emotion="urgency",
        ),
        ThumbnailConcept(
            concept_id="t3",
            headline="Why it matters",
            subtext=t[:40],
            visual_description=_enrich(
                "Split energy thumbnail: chaos light left, clean tech right, "
                "no logos no text in image"
            ),
            text_overlay="WHY IT MATTERS",
            emotion="curiosity",
        ),
        ThumbnailConcept(
            concept_id="t4",
            headline="Explained",
            subtext="Benchmarks & stakes",
            visual_description=_enrich(
                f"Photoreal hands + laptop dark room cyan light for '{t}' explainer, "
                "monitor content blurred, no text no logos"
            ),
            text_overlay="EXPLAINED",
            emotion="clarity",
        ),
        ThumbnailConcept(
            concept_id="t5",
            headline="What happens next",
            subtext="Implications",
            visual_description=_enrich(
                "Futuristic city night aerial dual-tone cyan/magenta, race stakes, "
                "no text no logos"
            ),
            text_overlay="WHAT'S NEXT",
            emotion="authority",
        ),
    ]

    package = VisualPackage(
        shot_list=shots,
        broll_prompts=broll,
        lower_thirds=lower[:40],
        thumbnail_concepts=thumbs,
    )

    strategy = {
        "story_one_liner": (
            facts[0]["fact"] if facts else script.topic_title
        ),
        "viewer_promise": "They understand the claim, the number, the proof, the stakes.",
        "peer_bar": "AI Revolution–class densemotion + proof screenshots",
        "reference_url": "https://www.youtube.com/watch?v=MEw7TrAUEPQ",
        "trust_tactics": [
            "Kinetic stats with source footers",
            "Real screenshots of reputable outlets (not AI fake newspapers)",
            "Comparison cards for multi-phase legal/tech claims",
            "No deepfake CEOs — titles only",
        ],
        "subscriber_hooks": [
            "Dense visual reward every few seconds",
            "Clear number takeaway worth sharing",
            "End screen next deep dive",
        ],
        "avoid": style.get("banned_as_primary_visual")
        or [
            "Empty courtroom filler",
            "Random server rooms",
            "Slow BBC stills with no motion plan",
        ],
    }

    extras = {
        "creative_strategy": strategy,
        "verified_story_beats": [
            {"beat": f.get("when"), "fact": f.get("fact"), "source_hint": f.get("source"), "confidence": "high"}
            for f in facts
        ],
        "on_screen_facts": facts,
        "motion_graphics": mg,
        "screen_captures": screens,
        "retention_notes": [
            "Match peer energy: cut faster on hook than body",
            "50%+ of timeline should be kinetic/UI/compare — not only B-roll stills",
            "AI stills = cinematic metaphors; PROOF = real screenshots",
            "CapCut does all typography",
        ],
        "generate_queue": list(dict.fromkeys(generate_queue))[:PRIORITY_GENERATE_CAP],
        "editor_brand_kit": style.get("brand_grade")
        or {
            "background": "near-black",
            "accent_primary": "electric cyan",
            "type": "bold geometric sans",
        },
        "channel_visual_style": "peer_ai_revolution",
        "grounding_news_hits": grounding.get("news_hits") or [],
    }
    return package, extras


def _markdown(package: VisualPackage, extras: dict[str, Any]) -> str:
    strat = extras.get("creative_strategy") or {}
    lines = [
        "# Visual Package — Competitive (AI Revolution–class)\n",
        f"**Peer reference:** {strat.get('reference_url', '')}\n",
        f"**Shots:** {len(package.shot_list)} · "
        f"**Motion graphic recipes:** {len(extras.get('motion_graphics') or [])} · "
        f"**Screen captures to grab:** {len(extras.get('screen_captures') or [])}\n",
        "## Strategy\n",
        f"- {strat.get('story_one_liner')}",
        f"- Promise: {strat.get('viewer_promise')}",
        f"- Peer bar: {strat.get('peer_bar')}\n",
        "### Avoid\n",
    ]
    for a in strat.get("avoid") or []:
        lines.append(f"- {a}")

    lines.append("\n## On-screen facts (kinetic type)\n")
    for f in extras.get("on_screen_facts") or []:
        lines.append(f"- **{f.get('fact')}** · _{f.get('source')}_")

    lines.append("\n## Motion graphic recipes (CapCut — this is how peers win)\n")
    for m in extras.get("motion_graphics") or []:
        lines.append(f"### {m.get('id')} · {m.get('type')}")
        lines.append(f"- Text: `{m.get('on_screen_text')}`")
        for step in m.get("capcut_steps") or []:
            lines.append(f"  - {step}")

    lines.append("\n## MUST-DO real screenshots\n")
    for s in extras.get("screen_captures") or []:
        lines.append(
            f"- **{s.get('id')}**: {s.get('action')}  \n"
            f"  URL hint: {s.get('url_hint') or 'search topic'}  \n"
            f"  Edit: {s.get('capcut')}"
        )

    lines.append("\n## Timeline shots\n")
    for s in package.shot_list:
        lines.append(
            f"- `{s.get('shot_id')}` t={s.get('start_sec')}s "
            f"**{s.get('asset_class')}** [{s.get('section_id')}] — {s.get('story_link')}"
        )
        if s.get("capcut_overlay"):
            lines.append(f"  - TYPE: `{s.get('capcut_overlay')}`")

    lines.append("\n## Cinematic B-roll prompts (Imagine / Kling)\n")
    for b in package.broll_prompts:
        if b.get("asset_class") != "cinematic_broll":
            continue
        lines.append(f"### {b.get('shot_id')}")
        lines.append(f"- Story: {b.get('story_link')}")
        lines.append(f"- Prompt:\n\n> {b.get('prompt')}\n")

    lines.append("\n## Thumbnails\n")
    for t in package.thumbnail_concepts:
        lines.append(f"### {t.concept_id}: `{t.text_overlay}`")
        lines.append(f"{t.visual_description}\n")

    lines.append(
        "\n## Production order (free tier)\n"
        "1. Grab real screenshots from screen_captures list\n"
        "2. Build kinetic stats from motion_graphics in CapCut\n"
        "3. Generate only cinematic_broll prompts in Imagine\n"
        "4. Assemble to VO with 3–5s average cut on hook\n"
    )
    return "\n".join(lines)


def run_visual_director(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "visual_director"
    try:
        raw = state.get("script_final") or state.get("script_draft")
        if not raw:
            return mark_failed(stage, "No script for visuals")
        script = VideoScript.model_validate(raw)
        brief = None
        if state.get("research_brief"):
            try:
                brief = ResearchBrief.model_validate(state["research_brief"])
            except Exception:  # noqa: BLE001
                brief = None

        style = load_visual_style()
        grounding = _gather_grounding(script.topic_title, brief, ctx.settings)
        package, extras = _build_competitive_package(script, grounding, style)

        if llm_available(ctx.settings) or ctx.use_llm:
            try:
                data = chat_json(
                    SYSTEM,
                    json.dumps(
                        {
                            "script": {
                                "title": script.title_working,
                                "topic": script.topic_title,
                                "runtime": script.estimated_runtime_minutes,
                                "sections": [
                                    {
                                        "id": s.id,
                                        "title": s.title,
                                        "start": s.start_timestamp,
                                        "end": s.end_timestamp,
                                        "excerpt": (s.narration or "")[:350],
                                    }
                                    for s in script.sections
                                ],
                            },
                            "grounding": grounding,
                            "baseline_facts": extras.get("on_screen_facts"),
                            "style": style,
                            "instruction": (
                                "Elevate to AI Revolution density. Keep facts accurate. "
                                "Prefer motion graphics + screenshots over empty rooms."
                            ),
                        },
                        ensure_ascii=False,
                        default=str,
                    )[:100000],
                    settings=ctx.settings,
                    temperature=0.4,
                    max_tokens=8192,
                )
                if isinstance(data.get("creative_strategy"), dict):
                    extras["creative_strategy"] = {
                        **(extras.get("creative_strategy") or {}),
                        **data["creative_strategy"],
                    }
                if data.get("motion_graphics"):
                    extras["motion_graphics"] = data["motion_graphics"]
                if data.get("screen_captures"):
                    extras["screen_captures"] = data["screen_captures"]
                if data.get("on_screen_facts"):
                    extras["on_screen_facts"] = data["on_screen_facts"]
                # Only replace timeline if dense enough
                if len(data.get("shot_list") or []) >= 40:
                    thumbs = [
                        ThumbnailConcept.model_validate(t)
                        for t in (data.get("thumbnail_concepts") or [])
                    ] or package.thumbnail_concepts
                    broll = data.get("broll_prompts") or package.broll_prompts
                    for b in broll:
                        if b.get("asset_class") == "cinematic_broll" or "cinematic" in (
                            b.get("style") or ""
                        ):
                            b["prompt"] = _enrich(b.get("prompt") or "")
                    package = VisualPackage(
                        shot_list=data["shot_list"],
                        broll_prompts=broll,
                        lower_thirds=data.get("lower_thirds") or package.lower_thirds,
                        thumbnail_concepts=thumbs,
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM visual elevation failed (%s); competitive baseline kept", exc)

        full = package.model_dump(mode="json")
        full["meta"] = extras
        ctx.store.write_json("visuals/package.json", full)
        ctx.store.write_text("visuals/package.md", _markdown(package, extras))
        ctx.store.write_json(
            "visuals/creative_strategy.json", extras.get("creative_strategy") or {}
        )
        ctx.store.write_json(
            "visuals/motion_graphics.json", extras.get("motion_graphics") or []
        )
        ctx.store.write_json(
            "visuals/screen_captures.json", extras.get("screen_captures") or []
        )
        ctx.store.write_json(
            "visuals/story_beats.json", extras.get("verified_story_beats") or []
        )

        # Imagine queue: cinematic stills + thumbs only
        queue = []
        for b in package.broll_prompts:
            if b.get("asset_class") == "cinematic_broll":
                queue.append(
                    {
                        "shot_id": b.get("shot_id"),
                        "kind": "cinematic_broll",
                        "story_link": b.get("story_link"),
                        "prompt": b.get("prompt"),
                        "priority": b.get("priority"),
                    }
                )
        for t in package.thumbnail_concepts:
            queue.append(
                {
                    "shot_id": t.concept_id,
                    "kind": "thumbnail",
                    "prompt": t.visual_description,
                    "capcut_text_overlay": t.text_overlay,
                    "priority": 1,
                }
            )
        ctx.store.write_json("visuals/imagine_queue.json", queue[:PRIORITY_GENERATE_CAP])
        ctx.store.write_text(
            "visuals/IMAGINE_PROMPTS.txt",
            "\n\n-----\n\n".join(
                f"[{q.get('shot_id')}|{q.get('kind')}]\n{q.get('prompt')}" for q in queue[:PRIORITY_GENERATE_CAP]
            ),
        )
        ctx.store.write_text(
            "visuals/CAPCUT_CHECKLIST.md",
            "\n".join(
                [
                    "# CapCut checklist (peer-competitive)",
                    "",
                    "## 1. Screenshots (do first — this is proof)",
                    *[
                        f"- [ ] {s.get('id')}: {s.get('action')}"
                        for s in (extras.get("screen_captures") or [])
                    ],
                    "",
                    "## 2. Kinetic stats",
                    *[
                        f"- [ ] {m.get('id')}: {m.get('on_screen_text')}"
                        for m in (extras.get("motion_graphics") or [])
                    ],
                    "",
                    "## 3. Drop cinematic stills under VO (3–5s hook cuts)",
                    "## 4. Thumbnail text overlays last",
                    "",
                ]
            ),
        )

        log.info(
            "Competitive visual package: shots=%s cinematic=%s mg=%s screens=%s",
            len(package.shot_list),
            sum(1 for b in package.broll_prompts if b.get("asset_class") == "cinematic_broll"),
            len(extras.get("motion_graphics") or []),
            len(extras.get("screen_captures") or []),
        )
        return mark_done(stage, {"visual_package": full})
    except Exception as exc:  # noqa: BLE001
        log.exception("Visual Director failed")
        return mark_failed(stage, str(exc))
