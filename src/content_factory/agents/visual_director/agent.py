"""Visual Director — high-retention, photorealistic shot design for subscriber growth.

Goals:
- Dense visual coverage for 12–16 min VO (cut every ~5–8s where possible)
- Photorealistic Grok Imagine / stock prompts (no watermarks, no on-image text)
- Thumbnail concepts optimized for CTR and new subscribers
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import ThumbnailConcept, VideoScript, VisualPackage
from content_factory.state import PipelineState
from content_factory.tools.llm import chat_json, llm_available
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

# High-retention pacing: aim for a visual change this often (seconds)
TARGET_SHOT_SECONDS = 6.0
# Free-tier priority: generate these first (Imagine / export queue)
PRIORITY_GENERATE_CAP = 24

PHOTOREAL_SUFFIX = (
    "Ultra photorealistic documentary still, shot on ARRI Alexa 35 with 35mm "
    "prime lens, natural cinematic color grade, shallow depth of field where "
    "appropriate, realistic skin and material textures, physically accurate "
    "lighting, no CGI plastic look, no illustration, no cartoon, no 3D render "
    "style, no stock-photo watermark, no logo watermark, no text overlay, "
    "no captions, no UI chrome, no brand trademarks, clean frame edges, "
    "YouTube 16:9 composition with safe margins."
)

SYSTEM = f"""You are the Visual Director for **Tech Frontier**, a high-retention tech YouTube channel.
Your #1 job is **viewer retention and subscriber growth** through dense, scroll-stopping, photorealistic visuals.

For a ~12–16 minute video you MUST produce a dense shot list:
- Target roughly **one visual change every {int(TARGET_SHOT_SECONDS)} seconds**
- Minimum **8–12 distinct shots per major section** (hook can be denser: every 2–4s)
- Mix: cold-open punches, B-roll, macro detail, wide establishing, reaction/context, abstract data-as-physical-metaphor, end-screen calm

PROMPT RULES for every broll/image prompt (non-negotiable):
1. **Photorealistic only** — real-world photography look, not illustration
2. **No watermarks, no logos, no readable text, no UI mockups with real brands**
3. **No celebrity/real-person faces** unless generic unrecognizable crowd
4. Start with subject + action, then setting, camera, lighting, mood
5. End with: photorealistic, no watermark, no text
6. Optimized for **Grok Imagine** (still) and reusable for Kling/Runway (motion note optional)
7. Prefer concrete objects, rooms, hands, documents, city streets, labs, court exteriors, server rooms — not vague "tech background"

THUMBNAILS (5 concepts):
- High CTR for curiosity + authority (not clickbait the video cannot pay off)
- Visual description for Imagine: face optional only if generic; prefer symbolic/object-led
- text_overlay is for CapCut later — **image itself has NO text**
- emotion field: curiosity | urgency | authority | shock | clarity

Return JSON:
{{
  "shot_list": [
    {{
      "shot_id": "s001",
      "section_id": "hook",
      "start_sec": 0,
      "duration_sec": 4,
      "type": "cold-open|b-roll|macro|wide|graphic-meta|end-card",
      "purpose": "retention|clarity|emotion|proof|cta",
      "on_screen_action": "what viewer sees",
      "description": "editor note",
      "priority": 1
    }}
  ],
  "broll_prompts": [
    {{
      "shot_id": "s001",
      "section_id": "hook",
      "provider_hints": ["grok_imagine", "kling", "runway", "stock"],
      "aspect_ratio": "16:9",
      "style": "photoreal_documentary",
      "prompt": "full photoreal prompt for image generation",
      "negative_cues": "watermark, text, logo, cartoon, blurry, low-res",
      "stock_keywords": ["keyword1", "keyword2"],
      "motion_hint": "optional slow push-in for video tools",
      "priority": 1
    }}
  ],
  "lower_thirds": [
    {{"text": "short label", "when": "section_id or timestamp", "style": "minimal tech"}}
  ],
  "thumbnail_concepts": [
    {{
      "concept_id": "t1",
      "headline": "title for packaging",
      "subtext": "secondary",
      "visual_description": "photoreal Imagine prompt WITHOUT any text in the image",
      "text_overlay": "SHORT CAPCUT TEXT",
      "emotion": "curiosity"
    }}
  ],
  "retention_notes": ["why these visuals convert / retain"],
  "generate_queue": ["shot_ids in free-tier generation order"]
}}

Priority 1 = must-generate free tier; 2 = important; 3 = nice-to-have.
Cover the FULL runtime implied by section timestamps — do not stop after 10 shots.
"""


def _parse_ts(ts: str) -> float:
    """MM:SS or M:SS → seconds."""
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


def _section_duration_sec(sec: Any, fallback_words: int, wpm: int = 150) -> float:
    start = _parse_ts(getattr(sec, "start_timestamp", "00:00"))
    end = _parse_ts(getattr(sec, "end_timestamp", "00:00"))
    if end > start:
        return max(end - start, 8.0)
    words = len((getattr(sec, "narration", "") or "").split()) or fallback_words
    return max(words / wpm * 60.0, 12.0)


def _enrich_prompt(base: str, topic: str) -> str:
    base = (base or "").strip()
    if not base:
        base = f"Photorealistic documentary B-roll related to {topic}"
    # Strip instruction to add text
    base = re.sub(r"\bwith text\b.*$", "", base, flags=re.I).strip()
    if "photoreal" not in base.lower():
        base = f"{base.rstrip('.')}. {PHOTOREAL_SUFFIX}"
    else:
        if "watermark" not in base.lower():
            base = f"{base.rstrip('.')}, no watermark, no text overlay, no logos"
    return base


def _topic_visual_seeds(topic: str) -> list[str]:
    """Large library of concrete photoreal seed scenes (unique variety for long VO)."""
    t = topic.lower()
    legal_social = any(
        k in t
        for k in (
            "meta",
            "facebook",
            "social",
            "nuisance",
            "court",
            "ruling",
            "lawsuit",
            "section 230",
            "moderation",
        )
    )
    if legal_social:
        return [
            "Exterior of a modern glass federal courthouse at golden hour, low angle, tiny silhouettes on steps, city skyline bokeh, photojournalism",
            "Dim content-moderation ops room with rows of monitors showing abstract blurred feeds only (no readable text, no logos), cyan desk light, empty chairs",
            "Close-up of thick legal briefs and a wooden gavel on dark oak desk, window side light, dust motes, editorial still life",
            "Hands holding a smartphone at night, screen glow only, city window reflections, intimate documentary, face out of frame",
            "Data center aisle with blue LED server racks receding into distance, industrial scale, cool humidity haze",
            "Busy city street at dusk, pedestrians looking at phones, neon and traffic bokeh, candid street photography, no readable brand signs",
            "Empty modern courtroom interior, wood bench and flags soft in background (no readable seals), volumetric light rays",
            "Macro of a fiber-optic cable bundle glowing cyan and amber, extreme detail, dark background",
            "Nighttime newsroom with empty desks and glowing monitors (blurred screens, no text), rain on windows",
            "Overhead shot of a conference table covered in printed legal packets (text illegible), coffee cups, dramatic top light",
            "Anonymous crowd walking through a transit hub, motion blur bodies, one sharp phone in foreground",
            "Security operations wall of abstract network graphs as soft light shapes (no legible UI), dark room",
            "Close-up of a judge's empty chair and polished wood dais, solemn atmosphere, shallow DOF",
            "Teenagers and adults in a public square all looking at phones, golden hour, human stakes storytelling",
            "Server room door ajar with cold light spilling into a dark corridor, thriller documentary mood",
            "Stack of hard drives and ethernet cables on a metal shelf, gritty macro documentary",
            "Rain-soaked glass reflecting abstract social-app color blobs (not logos), shallow focus",
            "Capitol-style stone columns with stormy sky (generic civic architecture, no specific building text)",
            "Close-up of redacted-style black bars on paper (artistic, not real secrets), pen beside, high contrast",
            "Wide night city from rooftop, long-exposure car lights, lonely silhouette looking at phone",
            "Hands typing on a mechanical keyboard, RGB soft bokeh, code out of focus on screen (illegible)",
            "Drone-like elevated view of suburban houses with window light, quiet stakes of online harm offline",
            "Photoreal scales of justice in brass on black velvet, single key light, premium product-editorial",
            "Blurred emergency vehicle lights reflected in a puddle at night, tense documentary",
            "Library law section shelves, warm tungsten, dust in light beam, scholarly calm",
            "Split-diopter style still: gavel sharp left, distant city lights soft right, cinematic",
            "Wearable POV style: walking into a glass lobby (no logos), reflections of people with phones",
            "Macro of a smartphone camera lens reflecting a courtroom-like interior abstractly",
            "Empty call-center style cubicles after hours, one monitor still on (blurred), melancholy tech",
            "Sunrise over a tech campus skyline with glass buildings (generic, no trademarks), hopeful tone",
        ]
    return [
        "Modern research lab bench with precision instruments and soft overhead LEDs, science documentary",
        "Extreme macro of a silicon wafer under inspection light, rainbow diffraction, cleanroom atmosphere",
        "Night skyline with light trails suggesting networks, long exposure urban photography",
        "Engineer hands assembling a circuit board under magnifier light, shallow DOF",
        "Robot arm in a factory cage with sparks soft in background, industrial photoreal",
        "Satellite dish farm at dusk under dramatic clouds, wide establishing",
        "Battery cells on a test bench with alligator clips, product engineering still",
        "Crowded trade-show floor abstract lights (no readable booth text), energetic bokeh",
        "Quiet university hallway with open lab door spilling white light",
        "Macro of cooling liquid circulating through clear tubes, high tech aesthetic",
        "Driver POV on a highway at night with HUD-like reflections (no legible UI text)",
        "Wind turbines on a ridge at blue hour, clean energy documentary",
        "3D-printed prototype part in a workshop vice, tactile photoreal",
        "Globe on a desk with fiber cables around it, soft office light (no brand marks)",
        "Oscilloscope-like curves as abstract green light only (no readable labels), dark lab",
    ]


_CAMERA_VARIATIONS = [
    "shot on 35mm prime, eye level",
    "low angle heroic framing",
    "high angle observational",
    "extreme close-up macro",
    "wide establishing shot",
    "medium shot with environmental context",
    "Dutch angle subtle tension",
    "telephoto compression from distance",
]


_LIGHT_VARIATIONS = [
    "golden hour natural light",
    "cool blue hour",
    "hard single key light noir",
    "soft window light",
    "practical neon accents",
    "overcast softbox sky",
    "volumetric god rays",
    "moonlight and practicals",
]


def _heuristic_dense_visuals(script: VideoScript) -> VisualPackage:
    """Build a dense shot list from section durations without LLM."""
    shots: list[dict[str, Any]] = []
    broll: list[dict[str, Any]] = []
    lower: list[dict[str, Any]] = []
    generate_queue: list[str] = []
    shot_n = 0
    global_t = 0.0
    seeds = _topic_visual_seeds(script.topic_title)
    seed_i = 0

    type_cycle = ["b-roll", "macro", "wide", "b-roll", "graphic-meta"]

    for sec in script.sections:
        dur = _section_duration_sec(sec, fallback_words=80)
        n_shots = max(3, int(math.ceil(dur / TARGET_SHOT_SECONDS)))
        if sec.id == "hook":
            n_shots = max(n_shots, 6)
            slot = max(2.5, dur / n_shots)
        else:
            slot = dur / n_shots

        cues = list(sec.visual_cues or []) or [sec.title]
        lower.append(
            {
                "text": sec.title[:40],
                "when": sec.id,
                "style": "minimal tech lower-third",
            }
        )

        for i in range(n_shots):
            shot_n += 1
            sid = f"s{shot_n:03d}"
            stype = "cold-open" if sec.id == "hook" and i < 2 else type_cycle[i % len(type_cycle)]
            if sec.id == "cta":
                stype = "end-card" if i == n_shots - 1 else "b-roll"
            purpose = (
                "emotion"
                if sec.id == "hook"
                else "cta"
                if sec.id == "cta"
                else "clarity"
                if i % 3 == 0
                else "retention"
            )
            cue = cues[i % len(cues)]
            seed = seeds[seed_i % len(seeds)]
            cam = _CAMERA_VARIATIONS[seed_i % len(_CAMERA_VARIATIONS)]
            light = _LIGHT_VARIATIONS[seed_i % len(_LIGHT_VARIATIONS)]
            seed_i += 1
            priority = 1 if (sec.id in {"hook", "why_it_matters"} or i < 2) else (2 if i < 5 else 3)

            start_sec = global_t + i * slot
            shots.append(
                {
                    "shot_id": sid,
                    "section_id": sec.id,
                    "start_sec": round(start_sec, 1),
                    "duration_sec": round(slot, 1),
                    "type": stype,
                    "purpose": purpose,
                    "on_screen_action": cue,
                    "description": f"{sec.title}: beat {i+1}/{n_shots} — {cue}",
                    "priority": priority,
                }
            )

            prompt_core = (
                f"{seed}. {cam}, {light}. "
                f"Story beat for section '{sec.title}': {cue}. "
                f"Thematic context: {script.topic_title}. "
                f"Unique frame variation #{shot_n}."
            )
            broll.append(
                {
                    "shot_id": sid,
                    "section_id": sec.id,
                    "provider_hints": ["grok_imagine", "kling", "runway", "stock"],
                    "aspect_ratio": "16:9",
                    "style": "photoreal_documentary",
                    "prompt": _enrich_prompt(prompt_core, script.topic_title),
                    "negative_cues": (
                        "watermark, logo, text, caption, subtitle, UI, cartoon, "
                        "illustration, 3d render, blurry, low resolution, stock stamp"
                    ),
                    "stock_keywords": [
                        script.topic_title[:40],
                        sec.id,
                        stype,
                        "documentary",
                        "photoreal",
                    ],
                    "motion_hint": "slow cinematic push-in or subtle parallax, 6s",
                    "priority": priority,
                }
            )
            if priority == 1:
                generate_queue.append(sid)

        global_t += dur

    # Ensure generate_queue has enough variety up to cap
    for item in broll:
        if item["shot_id"] not in generate_queue and len(generate_queue) < PRIORITY_GENERATE_CAP:
            generate_queue.append(item["shot_id"])

    thumbs = [
        ThumbnailConcept(
            concept_id="t1",
            headline=script.title_working[:70],
            subtext="What this ruling really means",
            visual_description=_enrich_prompt(
                "Split-frame photoreal still: left half chaotic phone screens as abstract "
                "light (no readable UI), right half empty modern courtroom bench with "
                "dramatic side light, high contrast for YouTube thumbnail base",
                script.topic_title,
            ),
            text_overlay="META FINED?",
            emotion="curiosity",
        ),
        ThumbnailConcept(
            concept_id="t2",
            headline="The $567M question",
            subtext="Platforms vs public nuisance law",
            visual_description=_enrich_prompt(
                "Photoreal close-up of brass scales of justice beside a dark smartphone "
                "face-down, single hard key light, black background, premium editorial",
                script.topic_title,
            ),
            text_overlay="$567M RULING",
            emotion="urgency",
        ),
        ThumbnailConcept(
            concept_id="t3",
            headline="Why this changes platforms",
            subtext="Section 230 under pressure",
            visual_description=_enrich_prompt(
                "Wide photoreal shot of glass tech campus exterior at blue hour with "
                "stormy sky, no logos, cinematic thriller mood for news explainer",
                script.topic_title,
            ),
            text_overlay="WHAT CHANGES",
            emotion="authority",
        ),
        ThumbnailConcept(
            concept_id="t4",
            headline="Inside the moderation machine",
            subtext="Systems under the microscope",
            visual_description=_enrich_prompt(
                "Photoreal over-the-shoulder of empty moderation desk, multiple monitors "
                "with abstract blurred content (no text), cool cyan grade, investigative",
                script.topic_title,
            ),
            text_overlay="EXPLAINED",
            emotion="clarity",
        ),
        ThumbnailConcept(
            concept_id="t5",
            headline="What it means for you",
            subtext="Speech, safety, and power",
            visual_description=_enrich_prompt(
                "Photoreal hand holding phone in foreground, soft-focus crowd of people "
                "in city square behind, golden hour, human stakes storytelling",
                script.topic_title,
            ),
            text_overlay="FOR YOU",
            emotion="shock",
        ),
    ]

    pkg = VisualPackage(
        shot_list=shots,
        broll_prompts=broll,
        lower_thirds=lower,
        thumbnail_concepts=thumbs,
    )
    # Stash extra fields via model dump later — VisualPackage is dict-friendly lists
    # Attach metadata on first shot list item is hacky; write extras in run_visual_director
    return pkg


def _merge_llm_package(
    base: VisualPackage, data: dict[str, Any], script: VideoScript
) -> VisualPackage:
    try:
        thumbs = [
            ThumbnailConcept.model_validate(t)
            for t in data.get("thumbnail_concepts") or []
        ]
        if len(thumbs) < 3:
            thumbs = list(base.thumbnail_concepts)
        # Enrich all prompts
        broll = []
        for item in data.get("broll_prompts") or base.broll_prompts:
            item = dict(item)
            item["prompt"] = _enrich_prompt(
                item.get("prompt") or "", script.topic_title
            )
            item.setdefault("aspect_ratio", "16:9")
            item.setdefault("style", "photoreal_documentary")
            item.setdefault(
                "negative_cues",
                "watermark, logo, text, cartoon, illustration, low-res",
            )
            item.setdefault("provider_hints", ["grok_imagine", "kling", "runway", "stock"])
            broll.append(item)
        shots = data.get("shot_list") or base.shot_list
        if len(shots) < max(20, len(base.shot_list) // 2):
            # LLM under-delivered density — keep dense base, merge high-priority LLM prompts
            log.warning(
                "LLM shot list too sparse (%s); keeping dense heuristic base",
                len(shots),
            )
            return base.model_copy(
                update={
                    "thumbnail_concepts": thumbs or base.thumbnail_concepts,
                    "lower_thirds": data.get("lower_thirds") or base.lower_thirds,
                }
            )
        return VisualPackage(
            shot_list=shots,
            broll_prompts=broll or base.broll_prompts,
            lower_thirds=data.get("lower_thirds") or base.lower_thirds,
            thumbnail_concepts=thumbs or base.thumbnail_concepts,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM visual merge failed: %s", exc)
        return base


def _package_markdown(package: VisualPackage, extras: dict[str, Any]) -> str:
    lines = [
        "# Visual Package — Retention & Subscriber Growth\n",
        f"**Shots:** {len(package.shot_list)}  ",
        f"**B-roll prompts:** {len(package.broll_prompts)}  ",
        f"**Target cut pace:** ~{TARGET_SHOT_SECONDS:.0f}s  ",
        f"**Free-tier generate first:** {len(extras.get('generate_queue') or [])}\n",
        "## Retention notes\n",
    ]
    for n in extras.get("retention_notes") or []:
        lines.append(f"- {n}")
    lines.append("\n## Shot list (timeline)\n")
    for s in package.shot_list:
        lines.append(
            f"- `{s.get('shot_id')}` [{s.get('section_id')}] "
            f"t={s.get('start_sec')}s +{s.get('duration_sec')}s "
            f"**{s.get('type')}** p{s.get('priority')}: {s.get('description')}"
        )
    lines.append("\n## Photoreal B-roll / Imagine prompts\n")
    for b in package.broll_prompts:
        lines.append(f"### {b.get('shot_id')} (priority {b.get('priority', '?')})")
        lines.append(f"- Section: `{b.get('section_id')}`")
        lines.append(f"- Prompt:\n\n> {b.get('prompt')}\n")
        lines.append(f"- Avoid: {b.get('negative_cues')}")
        lines.append(f"- Motion: {b.get('motion_hint', 'n/a')}\n")
    lines.append("\n## Free-tier generate queue\n")
    for sid in extras.get("generate_queue") or []:
        lines.append(f"- {sid}")
    lines.append("\n## Thumbnails (text added in CapCut — image has no text)\n")
    for t in package.thumbnail_concepts:
        lines.append(f"### {t.concept_id}: {t.headline}")
        lines.append(f"- Emotion: {t.emotion}")
        lines.append(f"- CapCut overlay: `{t.text_overlay}`")
        lines.append(f"- Imagine prompt:\n\n> {t.visual_description}\n")
    lines.append("\n## Lower thirds\n")
    for lt in package.lower_thirds:
        lines.append(f"- **{lt.get('text')}** @ {lt.get('when')} ({lt.get('style', '')})")
    lines.append(
        "\n## Editor notes\n"
        "- Cut on every shot_id; if VO overruns, hold last frame with slow Ken Burns.\n"
        "- Never leave static slides >8s without zoom/pan.\n"
        "- Add captions + lower-thirds in CapCut (not baked into AI images).\n"
        "- No watermarks: reject any asset with stamps; regenerate.\n"
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
        runtime = script.estimated_runtime_minutes or max(
            script.word_count / 150.0, 8.0
        )
        target_shots = max(40, int((runtime * 60) / TARGET_SHOT_SECONDS))

        package = _heuristic_dense_visuals(script)
        extras: dict[str, Any] = {
            "retention_notes": [
                f"Target ~{TARGET_SHOT_SECONDS:.0f}s visual pace across ~{runtime:.1f} min VO",
                f"Dense plan aims for ~{target_shots}+ shots for high retention",
                "Photoreal only; no watermarks; text overlays only in CapCut",
                "Hook denser (2–4s) to stop scroll; CTA calmer for end screen",
                "Priority-1 queue first under free Imagine quota",
            ],
            "generate_queue": [
                b["shot_id"]
                for b in sorted(
                    package.broll_prompts, key=lambda x: int(x.get("priority") or 9)
                )
            ][:PRIORITY_GENERATE_CAP],
            "target_shot_seconds": TARGET_SHOT_SECONDS,
            "estimated_runtime_minutes": runtime,
        }

        if llm_available(ctx.settings) or ctx.use_llm:
            try:
                # Compact script for LLM — full narration can blow free context
                compact = {
                    "title_working": script.title_working,
                    "topic_title": script.topic_title,
                    "estimated_runtime_minutes": runtime,
                    "word_count": script.word_count,
                    "sections": [
                        {
                            "id": s.id,
                            "title": s.title,
                            "start_timestamp": s.start_timestamp,
                            "end_timestamp": s.end_timestamp,
                            "narration_excerpt": (s.narration or "")[:500],
                            "visual_cues": s.visual_cues,
                            "on_screen_text": s.on_screen_text,
                        }
                        for s in script.sections
                    ],
                    "min_shots": target_shots,
                    "channel": ctx.style.get("channel_name", "Tech Frontier"),
                }
                data = chat_json(
                    SYSTEM,
                    json.dumps(compact, ensure_ascii=False),
                    settings=ctx.settings,
                    temperature=0.45,
                    max_tokens=8192,
                )
                package = _merge_llm_package(package, data, script)
                if data.get("generate_queue"):
                    extras["generate_queue"] = list(data["generate_queue"])[
                        :PRIORITY_GENERATE_CAP
                    ]
                if data.get("retention_notes"):
                    extras["retention_notes"] = list(data["retention_notes"]) + extras[
                        "retention_notes"
                    ][:2]
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM visual director failed (%s); dense heuristic package", exc)

        # Re-enrich all prompts one more time
        package = package.model_copy(
            update={
                "broll_prompts": [
                    {
                        **b,
                        "prompt": _enrich_prompt(
                            b.get("prompt") or "", script.topic_title
                        ),
                    }
                    for b in package.broll_prompts
                ],
                "thumbnail_concepts": [
                    t.model_copy(
                        update={
                            "visual_description": _enrich_prompt(
                                t.visual_description, script.topic_title
                            )
                        }
                    )
                    for t in package.thumbnail_concepts
                ],
            }
        )

        # Persist
        full_payload = package.model_dump(mode="json")
        full_payload["meta"] = extras
        ctx.store.write_json("visuals/package.json", full_payload)
        ctx.store.write_text(
            "visuals/package.md", _package_markdown(package, extras)
        )

        # Free-tier prompt export for Imagine batch
        queue_prompts = []
        by_id = {b.get("shot_id"): b for b in package.broll_prompts}
        for sid in extras.get("generate_queue") or []:
            if sid in by_id:
                queue_prompts.append(
                    {
                        "shot_id": sid,
                        "prompt": by_id[sid].get("prompt"),
                        "aspect_ratio": "16:9",
                        "priority": by_id[sid].get("priority"),
                    }
                )
        for t in package.thumbnail_concepts:
            queue_prompts.append(
                {
                    "shot_id": t.concept_id,
                    "prompt": t.visual_description,
                    "aspect_ratio": "16:9",
                    "priority": 1,
                    "kind": "thumbnail",
                    "capcut_text_overlay": t.text_overlay,
                }
            )
        ctx.store.write_json("visuals/imagine_queue.json", queue_prompts)
        ctx.store.write_text(
            "visuals/IMAGINE_PROMPTS.txt",
            "\n\n-----\n\n".join(
                f"[{q.get('shot_id')}] {q.get('prompt')}" for q in queue_prompts
            ),
        )

        log.info(
            "Visual package: %s shots, %s prompts, queue=%s",
            len(package.shot_list),
            len(package.broll_prompts),
            len(queue_prompts),
        )
        return mark_done(
            stage,
            {
                "visual_package": full_payload,
            },
        )
    except Exception as exc:  # noqa: BLE001
        log.exception("Visual Director failed")
        return mark_failed(stage, str(exc))
