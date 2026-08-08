"""Visual Director — news-grounded creative direction for Tech Frontier.

This is NOT a generic B-roll generator. For real-world news, inventions, and
public figures, every shot must serve the actual story: who, what, where, when,
stakes, proof, and sources. Credibility = subscribers.
"""

from __future__ import annotations

import json
import math
import re
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
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

TARGET_SHOT_SECONDS = 6.0
PRIORITY_GENERATE_CAP = 28

# Image-gen safe photoreal suffix — NO invented celebrity faces; NO fake logos
PHOTOREAL_NEWS = (
    "Ultra photorealistic investigative documentary still, natural color, "
    "shot like premium TV news B-roll / BBC documentary unit, ARRI Alexa look, "
    "physically accurate light, no stock-photo watermark, no text burned into "
    "frame, no fake UI screens with legible logos, no deepfake celebrity faces, "
    "no cartoon, 16:9 YouTube framing with safe margins."
)

SYSTEM = f"""You are the Executive Creative Director + Visual Director for **Tech Frontier**,
a serious tech/news explainer channel. Goal: **credibility and subscribers**.

You are covering REAL news, REAL products, REAL courts, REAL public figures.
GENERIC filler (random server rooms, random phones, random gavels with no story link)
is a FIREABLE offense. Every shot must answer: "Why does THIS image belong in THIS story?"

## Creative law (non-negotiable)
1. **Story-first.** Ground every shot in the research brief + verified news signals.
2. **Specificity.** Prefer: jurisdiction, court type, plaintiff (e.g. state AG), remedy type
   (civil penalty, injunctive relief), product surface (Instagram/Facebook teen features),
   mechanism (recommendation systems, age gates), appeal status — when known.
3. **Proof on screen.** Lower-thirds and CapCut overlays carry REAL facts + source names.
   Image itself has NO burned text.
4. **Public figures.** Do NOT generate photoreal likenesses of named living people
   (judges, AGs, CEOs). Use: empty podium + lower-third name, courthouse exterior,
   official-style press room empty lectern, documents, maps, product-in-environment.
5. **Brands.** Do not render trademark logos. Show platform *context* (teens on phones,
   parent settings screens as abstract blur, app store shelves abstract) + CapCut labels.
6. **Photoreal only.** No illustration. No watermark.
7. **Density.** ~1 visual change every {int(TARGET_SHOT_SECONDS)}s across full runtime.
8. **Brand of channel.** Authoritative, analytical, not tabloid. Trust > hype.

## Shot types (use deliberately)
- establishing_news: real place/jurisdiction energy (state capitol, federal/state courthouse)
- proof_graphic: CapCut fact card (amount, date, court) — describe graphic for editor
- mechanism: how the product/system works in human terms (age gates, feeds as abstract blur)
- stakeholder: parents, teens, teachers, policymakers (generic faces, not celebrities)
- document_trail: legal filings aesthetic (illegible text), hearing room, empty bench
- consequence: offline harm metaphor carefully (not exploitative of minors)
- reaction_industry: newsroom, analyst desk, appeal/PR empty mic stand
- end_brand: Tech Frontier soft CTA, clean

Return JSON:
{{
  "creative_strategy": {{
    "story_one_liner": "...",
    "viewer_promise": "what they understand by the end",
    "trust_tactics": ["on-screen sources", "..."],
    "subscriber_hooks": ["why they subscribe after this video"],
    "avoid": ["generic server rooms with no link", "deepfake faces", "..."]
  }},
  "verified_story_beats": [
    {{"beat": "...", "fact": "...", "source_hint": "BBC / court / AG", "confidence": "high|medium|low"}}
  ],
  "shot_list": [
    {{
      "shot_id": "s001",
      "section_id": "hook",
      "start_sec": 0,
      "duration_sec": 4,
      "type": "establishing_news|proof_graphic|mechanism|stakeholder|document_trail|consequence|reaction_industry|end_brand|cold-open",
      "purpose": "credibility|retention|clarity|emotion|proof|cta",
      "story_link": "WHY this shot is in THIS story (not generic)",
      "on_screen_action": "what we see",
      "capcut_overlay": "optional fact text for editor",
      "source_lower_third": "optional Source: BBC News",
      "description": "editor note",
      "priority": 1
    }}
  ],
  "broll_prompts": [
    {{
      "shot_id": "s001",
      "section_id": "hook",
      "story_link": "ties to New Mexico public nuisance penalty phase",
      "provider_hints": ["grok_imagine", "stock", "news_archive_search"],
      "aspect_ratio": "16:9",
      "style": "photoreal_news_documentary",
      "prompt": "story-specific photoreal prompt",
      "negative_cues": "watermark, logo, celebrity deepfake face, cartoon, burned-in text",
      "stock_keywords": ["New Mexico courthouse", "child online safety hearing"],
      "news_search_query": "optional exact search for real archive stills",
      "motion_hint": "slow push-in",
      "priority": 1
    }}
  ],
  "lower_thirds": [
    {{"text": "accurate label", "when": "section or time", "style": "news lower-third"}}
  ],
  "on_screen_facts": [
    {{"fact": "$567 million civil penalty (phase)", "source": "BBC / court coverage", "when": "hook"}}
  ],
  "thumbnail_concepts": [
    {{
      "concept_id": "t1",
      "headline": "honest but strong",
      "subtext": "...",
      "visual_description": "story-specific photoreal prompt NO text in image",
      "text_overlay": "SHORT CAPCUT TEXT",
      "emotion": "curiosity|urgency|authority|shock|clarity"
    }}
  ],
  "retention_notes": ["..."],
  "generate_queue": ["s001", "t1"],
  "editor_brand_kit": {{
    "palette": "dark navy + electric cyan accents + clean white type",
    "font_mood": "modern sans news",
    "end_screen": "subscribe + related child-safety / platform law video"
  }}
}}
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


def _section_duration_sec(sec: Any, fallback_words: int = 80, wpm: int = 150) -> float:
    start = _parse_ts(getattr(sec, "start_timestamp", "00:00"))
    end = _parse_ts(getattr(sec, "end_timestamp", "00:00"))
    if end > start:
        return max(end - start, 8.0)
    words = len((getattr(sec, "narration", "") or "").split()) or fallback_words
    return max(words / wpm * 60.0, 12.0)


def _enrich_prompt(base: str) -> str:
    base = (base or "").strip()
    if not base:
        return PHOTOREAL_NEWS
    if "photoreal" not in base.lower():
        base = f"{base.rstrip('.')}. {PHOTOREAL_NEWS}"
    elif "watermark" not in base.lower():
        base = f"{base.rstrip('.')}, no watermark, no burned-in text, no logos"
    return base


def _gather_visual_grounding(
    topic: str,
    brief: ResearchBrief | None,
    settings: Any,
) -> dict[str, Any]:
    """Pull live news signals so visuals track the real story."""
    queries = [
        topic,
        f"{topic} court ruling",
        f"{topic} public nuisance",
    ]
    if brief:
        if brief.key_claims:
            queries.append(brief.key_claims[0][:120])
        queries.append(f"{brief.topic_title} BBC OR Reuters OR AP")

    hits: list[dict[str, Any]] = []
    for q in queries[:4]:
        try:
            hits.extend(search_web(q, max_results=5, settings=settings))
        except Exception as exc:  # noqa: BLE001
            log.warning("Visual grounding search failed for %r: %s", q, exc)

    # Dedupe
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for h in hits:
        url = (h.get("url") or "").strip()
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        unique.append(h)

    return {
        "topic": topic,
        "brief_overview": (brief.overview[:800] if brief else ""),
        "brief_claims": (brief.key_claims[:8] if brief else []),
        "uncertainty_flags": (brief.uncertainty_flags if brief else []),
        "citations": (
            [c.model_dump() for c in (brief.citations[:10] if brief else [])]
        ),
        "news_hits": unique[:20],
    }


def _detect_story_profile(topic: str, grounding: dict[str, Any]) -> str:
    blob = " ".join(
        [
            topic,
            grounding.get("brief_overview") or "",
            " ".join(grounding.get("brief_claims") or []),
            " ".join(
                f"{h.get('title','')} {h.get('snippet','')}"
                for h in grounding.get("news_hits") or []
            ),
        ]
    ).lower()
    if any(
        k in blob
        for k in (
            "meta",
            "facebook",
            "instagram",
            "public nuisance",
            "new mexico",
            "child safety",
            "567",
            "375",
        )
    ):
        return "meta_nm_child_safety_public_nuisance"
    if any(k in blob for k in ("court", "lawsuit", "ruling", "fine", "settlement")):
        return "legal_tech_ruling"
    if any(k in blob for k in ("launch", "release", "model", "chip", "robot")):
        return "product_launch"
    return "general_tech_news"


def _meta_nm_story_pack() -> dict[str, Any]:
    """Verified creative pack for the New Mexico Meta public-nuisance penalty story.

    Grounded from major news coverage (BBC et al.): NM child-safety case;
    jury phase ~$375m; judge public-nuisance phase additional ~$567m;
    total cited ~$942m; Judge Bryan Biedscheid; fund for future harms;
    first-of-kind public nuisance label for a social platform; Meta appealing.
    """
    beats = [
        {
            "beat": "hook_stakes",
            "fact": "New Mexico court: Meta treated as public nuisance over child-safety harms",
            "source_hint": "BBC News / court coverage",
            "confidence": "high",
        },
        {
            "beat": "money_1",
            "fact": "Jury phase damages reported around $375 million",
            "source_hint": "NPR / trial coverage",
            "confidence": "high",
        },
        {
            "beat": "money_2",
            "fact": "Judge ordered additional ~$567 million civil penalty / abatement-style fund",
            "source_hint": "BBC News",
            "confidence": "high",
        },
        {
            "beat": "total",
            "fact": "Combined figure widely reported near $942 million",
            "source_hint": "BBC News",
            "confidence": "high",
        },
        {
            "beat": "first",
            "fact": "Coverage frames this as first time a social platform branded a public nuisance in this way",
            "source_hint": "BBC News",
            "confidence": "medium",
        },
        {
            "beat": "remedy",
            "fact": "Money framed for reducing future harms; platform feature limits for children discussed",
            "source_hint": "BBC / state AG coverage",
            "confidence": "medium",
        },
        {
            "beat": "appeal",
            "fact": "Meta says it will appeal",
            "source_hint": "company statements via wire/press",
            "confidence": "high",
        },
        {
            "beat": "people",
            "fact": "Judge Bryan Biedscheid; New Mexico AG Raúl Torrez as key public voice",
            "source_hint": "court / AG press",
            "confidence": "high",
        },
    ]

    # Story-specific visual seeds (NOT generic filler)
    seeds = [
        {
            "id": "nm_courthouse",
            "story_link": "Venue: New Mexico state court system handling AG child-safety case",
            "prompt": (
                "Photoreal exterior of a southwestern U.S. state courthouse in New Mexico "
                "style architecture, high desert light, American flags, journalists with "
                "cameras on steps as small figures, investigative news B-roll, no readable "
                "signs, no logos"
            ),
            "stock_keywords": [
                "New Mexico state courthouse",
                "Santa Fe court exterior",
                "press scrum courthouse",
            ],
            "news_search_query": "New Mexico First Judicial District Court Meta",
        },
        {
            "id": "ag_press",
            "story_link": "State power vs platform: NM Attorney General case frame",
            "prompt": (
                "Photoreal empty government press-briefing room with dual microphones on a "
                "wooden podium, state seal area intentionally out of focus/illegible, "
                "hard news lighting, no person at podium, no logos"
            ),
            "stock_keywords": ["attorney general press conference empty podium"],
            "news_search_query": "Raul Torrez Meta child safety press conference",
        },
        {
            "id": "teen_phone_parent",
            "story_link": "Alleged harm surface: children + Instagram/Facebook use",
            "prompt": (
                "Photoreal documentary: teenager's hands scrolling a phone on a couch while "
                "a parent watches with concern in soft background bokeh, warm home interior, "
                "screen content fully blurred with no UI or logos, sensitive non-exploitative"
            ),
            "stock_keywords": [
                "teen smartphone parent concern documentary",
                "youth social media home",
            ],
            "news_search_query": "Instagram teen safety parental controls",
        },
        {
            "id": "school_phone",
            "story_link": "Offline institutional stakes: schools/youth environments",
            "prompt": (
                "Photoreal American high-school hallway between classes, students with phones, "
                "lockers, natural window light, candid documentary, no brand logos, no text"
            ),
            "stock_keywords": ["high school hallway smartphones documentary"],
            "news_search_query": "schools social media addiction lawsuits",
        },
        {
            "id": "moderation_labor",
            "story_link": "Platform systems under scrutiny: moderation / safety ops",
            "prompt": (
                "Photoreal content-safety operations floor at night, many monitors with "
                "abstract blurred feeds only, tired empty chairs, cyan task lighting, "
                "no readable UI, no company logos — labor and systems, not sci-fi"
            ),
            "stock_keywords": ["content moderation office monitors"],
            "news_search_query": "Meta content moderation center",
        },
        {
            "id": "algorithm_human",
            "story_link": "Engagement systems vs youth safety (mechanism explainer)",
            "prompt": (
                "Photoreal extreme close-up of a phone screen edge reflecting a young user's "
                "eye out of focus, dark room, only soft screen glow, no UI legible, "
                "intimate documentary metaphor for infinite scroll"
            ),
            "stock_keywords": ["phone screen glow night documentary"],
            "news_search_query": "social media algorithmic feed youth",
        },
        {
            "id": "legal_filings",
            "story_link": "Document trail of multi-phase trial (jury then judge penalty)",
            "prompt": (
                "Photoreal overhead of dense printed legal motions and exhibits on a counsel "
                "table, yellow sticky tabs, coffee, text deliberately illegible, harsh "
                "fluorescent mixed with window light, pure courtroom documentary"
            ),
            "stock_keywords": ["litigation counsel table documents"],
            "news_search_query": "Meta New Mexico trial documents",
        },
        {
            "id": "empty_bench",
            "story_link": "Judge penalty phase (no deepfake of named judge)",
            "prompt": (
                "Photoreal empty elevated judicial bench in a modern U.S. state courtroom, "
                "leather chair, wood paneling, American flag soft bokeh, no seals readable, "
                "solemn available light"
            ),
            "stock_keywords": ["empty judge bench state courtroom"],
            "news_search_query": "Judge Bryan Biedscheid courtroom",
        },
        {
            "id": "abatement_fund",
            "story_link": "Remedy: civil penalty / fund framed to reduce future harms",
            "prompt": (
                "Photoreal abstract but grounded: hands counting paper evidence folders into "
                "an archive box labeled only with a blank tag (no text), municipal office "
                "setting, documentary still about abatement funds — no money porn"
            ),
            "stock_keywords": ["court settlement archive boxes"],
            "news_search_query": "public nuisance abatement fund",
        },
        {
            "id": "feature_limits",
            "story_link": "Injunctive flavor: limits on youth-facing product features",
            "prompt": (
                "Photoreal parent and teen negotiating a phone in kitchen at breakfast, "
                "screen blurred, warm realistic home photography, product-feature limits "
                "as human moment, no logos"
            ),
            "stock_keywords": ["parent teen phone rules kitchen"],
            "news_search_query": "Meta Instagram teen feature restrictions",
        },
        {
            "id": "appeal_path",
            "story_link": "Meta will appeal — process not final victory lap",
            "prompt": (
                "Photoreal exterior glass appellate courthouse or state supreme court "
                "building under stormy sky, wide establishing, no logos, news B-roll"
            ),
            "stock_keywords": ["appellate court exterior"],
            "news_search_query": "Meta appeal New Mexico ruling",
        },
        {
            "id": "industry_impact",
            "story_link": "Precedent risk for other platforms (TikTok/YouTube etc.) without logos",
            "prompt": (
                "Photoreal city at night with many people on phones on a transit platform, "
                "anonymous, documentary, multi-platform youth attention economy, no logos"
            ),
            "stock_keywords": ["commuters smartphones night documentary"],
            "news_search_query": "social media public nuisance other platforms",
        },
        {
            "id": "capitol_policy",
            "story_link": "Policy / AG wave of state actions on youth social media",
            "prompt": (
                "Photoreal state capitol dome at blue hour, southwestern U.S. feel, "
                "clean establishing shot for state AG litigation wave, no text"
            ),
            "stock_keywords": ["New Mexico state capitol blue hour"],
            "news_search_query": "state attorneys general social media lawsuits",
        },
        {
            "id": "newsroom_verify",
            "story_link": "Journalism verification beat — channel brand trust",
            "prompt": (
                "Photoreal newsroom desk with multiple muted monitors showing abstract "
                "maps and waveforms only, notepad, pen, late night, BBC-style seriousness, "
                "no logos, no readable headlines"
            ),
            "stock_keywords": ["investigative newsroom desk night"],
            "news_search_query": "Meta New Mexico $567 million BBC",
        },
    ]
    return {"beats": beats, "seeds": seeds}


def _story_seeds_for_profile(profile: str, topic: str) -> list[dict[str, Any]]:
    if profile == "meta_nm_child_safety_public_nuisance":
        return _meta_nm_story_pack()["seeds"]
    # Legal tech generic but still story-tied via topic string
    return [
        {
            "id": "court_est",
            "story_link": f"Legal venue energy for: {topic}",
            "prompt": (
                f"Photoreal U.S. courthouse exterior relevant to news story '{topic}', "
                "press cameras, documentary, no logos no text"
            ),
            "stock_keywords": [topic[:40], "courthouse exterior press"],
            "news_search_query": topic,
        },
        {
            "id": "docs",
            "story_link": f"Document trail for: {topic}",
            "prompt": (
                f"Photoreal counsel table stacked with filings about '{topic}', "
                "illegible text, documentary"
            ),
            "stock_keywords": ["litigation documents table"],
            "news_search_query": f"{topic} complaint filing",
        },
        {
            "id": "public_stake",
            "story_link": f"Human stakes for: {topic}",
            "prompt": (
                f"Photoreal ordinary people affected by issue in '{topic}', candid, "
                "respectful documentary, no celebrity faces"
            ),
            "stock_keywords": [topic[:30], "public impact documentary"],
            "news_search_query": topic,
        },
    ]


def _build_grounded_package(
    script: VideoScript,
    grounding: dict[str, Any],
    profile: str,
) -> tuple[VisualPackage, dict[str, Any]]:
    pack = (
        _meta_nm_story_pack()
        if profile == "meta_nm_child_safety_public_nuisance"
        else {"beats": [], "seeds": _story_seeds_for_profile(profile, script.topic_title)}
    )
    seeds = pack["seeds"]
    beats = pack.get("beats") or []

    shots: list[dict[str, Any]] = []
    broll: list[dict[str, Any]] = []
    lower: list[dict[str, Any]] = []
    on_screen_facts: list[dict[str, Any]] = []
    generate_queue: list[str] = []

    for b in beats:
        on_screen_facts.append(
            {
                "fact": b["fact"],
                "source": b.get("source_hint", ""),
                "when": b.get("beat", ""),
                "confidence": b.get("confidence", "medium"),
            }
        )

    # Fact cards as editor graphics (not AI images with text)
    for i, b in enumerate(beats[:6]):
        lower.append(
            {
                "text": b["fact"][:80],
                "when": b.get("beat"),
                "style": "news fact lower-third",
                "source": b.get("source_hint"),
            }
        )

    global_t = 0.0
    shot_n = 0
    seed_i = 0
    type_for = {
        "hook": "cold-open",
        "why_it_matters": "establishing_news",
        "explanation": "mechanism",
        "benchmarks_demos": "proof_graphic",
        "implications": "consequence",
        "bigger_picture": "reaction_industry",
        "cta": "end_brand",
    }

    for sec in script.sections:
        dur = _section_duration_sec(sec)
        n_shots = max(4, int(math.ceil(dur / TARGET_SHOT_SECONDS)))
        if sec.id == "hook":
            n_shots = max(n_shots, 8)
        slot = dur / n_shots
        base_type = type_for.get(sec.id, "establishing_news")

        for i in range(n_shots):
            shot_n += 1
            sid = f"s{shot_n:03d}"
            seed = seeds[seed_i % len(seeds)]
            seed_i += 1
            priority = 1 if sec.id in {"hook", "why_it_matters"} or i < 2 else (2 if i < 4 else 3)
            start_sec = global_t + i * slot
            stype = base_type if i > 0 else (
                "cold-open" if sec.id == "hook" else base_type
            )
            if i == n_shots // 2 and beats:
                stype = "proof_graphic"

            story_link = seed.get("story_link") or f"Supports section {sec.title} of {script.topic_title}"
            cue = (sec.visual_cues[i % len(sec.visual_cues)] if sec.visual_cues else sec.title)

            fact_overlay = ""
            source_lt = ""
            if beats and (i % 3 == 0):
                fb = beats[i % len(beats)]
                fact_overlay = fb["fact"][:90]
                source_lt = f"Source: {fb.get('source_hint', 'reporting')}"

            shots.append(
                {
                    "shot_id": sid,
                    "section_id": sec.id,
                    "start_sec": round(start_sec, 1),
                    "duration_sec": round(slot, 1),
                    "type": stype,
                    "purpose": "proof" if stype == "proof_graphic" else "credibility",
                    "story_link": story_link,
                    "on_screen_action": cue,
                    "capcut_overlay": fact_overlay,
                    "source_lower_third": source_lt,
                    "description": f"{sec.title} / {seed.get('id')}: {story_link}",
                    "priority": priority,
                }
            )

            if stype == "proof_graphic":
                prompt = (
                    "Photoreal empty news graphics desk with blank slate monitor glow "
                    "(no legible text), ready for lower-third fact cards in edit, "
                    "serious nightly news aesthetic — editor will superimpose verified numbers"
                )
            else:
                prompt = seed["prompt"]

            broll.append(
                {
                    "shot_id": sid,
                    "section_id": sec.id,
                    "story_link": story_link,
                    "provider_hints": ["grok_imagine", "stock", "news_archive_search"],
                    "aspect_ratio": "16:9",
                    "style": "photoreal_news_documentary",
                    "prompt": _enrich_prompt(prompt),
                    "negative_cues": (
                        "watermark, logo, trademark, deepfake celebrity face, "
                        "Mark Zuckerberg likeness, burned-in text, cartoon, stock stamp"
                    ),
                    "stock_keywords": seed.get("stock_keywords") or [script.topic_title],
                    "news_search_query": seed.get("news_search_query") or script.topic_title,
                    "motion_hint": "slow documentary push-in or parallax, 5–6s",
                    "priority": priority,
                }
            )
            if priority == 1:
                generate_queue.append(sid)

        global_t += dur

    # Fill queue
    for item in broll:
        if item["shot_id"] not in generate_queue and len(generate_queue) < PRIORITY_GENERATE_CAP:
            generate_queue.append(item["shot_id"])

    if profile == "meta_nm_child_safety_public_nuisance":
        thumbs = [
            ThumbnailConcept(
                concept_id="t1",
                headline="Meta branded a public nuisance",
                subtext="New Mexico child-safety case",
                visual_description=_enrich_prompt(
                    "Photoreal southwestern U.S. courthouse steps with press cameras, "
                    "tense golden hour, news thumbnail energy, no logos, no text, "
                    "no celebrity faces"
                ),
                text_overlay="PUBLIC NUISANCE",
                emotion="shock",
            ),
            ThumbnailConcept(
                concept_id="t2",
                headline="$567M more on child safety",
                subtext="On top of jury damages",
                visual_description=_enrich_prompt(
                    "Photoreal split: left teen hands on phone (screen blurred), right "
                    "empty judicial bench, high contrast news thumbnail, no logos no text"
                ),
                text_overlay="+$567M",
                emotion="urgency",
            ),
            ThumbnailConcept(
                concept_id="t3",
                headline="First of its kind?",
                subtext="Public nuisance meets social platforms",
                visual_description=_enrich_prompt(
                    "Photoreal state capitol dome southwestern dusk, authoritative policy "
                    "thumbnail base, no text no logos"
                ),
                text_overlay="LANDMARK?",
                emotion="authority",
            ),
            ThumbnailConcept(
                concept_id="t4",
                headline="What the court ordered",
                subtext="Penalty fund + youth feature pressure",
                visual_description=_enrich_prompt(
                    "Photoreal parent and teen with phone at kitchen table, concerned "
                    "documentary still, screen blurred, no logos no text"
                ),
                text_overlay="WHAT CHANGES",
                emotion="clarity",
            ),
            ThumbnailConcept(
                concept_id="t5",
                headline="Meta will appeal",
                subtext="Not the final word",
                visual_description=_enrich_prompt(
                    "Photoreal glass appellate courthouse stormy sky wide shot, "
                    "process-not-victory mood, no logos no text"
                ),
                text_overlay="APPEAL",
                emotion="curiosity",
            ),
        ]
        strategy = {
            "story_one_liner": (
                "A New Mexico court treated Meta as a public nuisance over youth harms, "
                "adding a massive civil penalty after jury damages — and Meta is appealing."
            ),
            "viewer_promise": (
                "Clear numbers, legal mechanism, youth-safety stakes, and what changes next."
            ),
            "trust_tactics": [
                "On-screen facts with source lower-thirds (BBC, court, AG)",
                "Separate jury damages vs judge penalty phase visually",
                "No deepfake public figures — names on lower-thirds only",
                "Show human stakeholders (parents/teens) not random sci-fi servers",
                "Flag uncertainty if script understates/overstates amounts",
            ],
            "subscriber_hooks": [
                "Viewers stay for accurate explainer they can trust",
                "End screen to next platform-law / child-safety deep dive",
                "Comment prompt: should public nuisance apply to feeds?",
            ],
            "avoid": [
                "Generic server rooms with no story link",
                "Fake Meta logos or Zuckerberg deepfakes",
                "Single wrong fine amount without phase context",
                "Exploitative imagery of child harm",
            ],
        }
    else:
        thumbs = [
            ThumbnailConcept(
                concept_id="t1",
                headline=script.title_working[:60],
                subtext="What actually happened",
                visual_description=_enrich_prompt(
                    f"Photoreal news establishing visual for '{script.topic_title}', "
                    "serious documentary, no logos no text"
                ),
                text_overlay="EXPLAINED",
                emotion="authority",
            ),
            ThumbnailConcept(
                concept_id="t2",
                headline=script.topic_title[:50],
                subtext="Why it matters",
                visual_description=_enrich_prompt(
                    f"Photoreal human-stakes still for '{script.topic_title}', no logos"
                ),
                text_overlay="WHY IT MATTERS",
                emotion="curiosity",
            ),
            ThumbnailConcept(
                concept_id="t3",
                headline="The real stakes",
                subtext=script.topic_title[:40],
                visual_description=_enrich_prompt(
                    f"Photoreal proof/document trail mood for '{script.topic_title}'"
                ),
                text_overlay="THE STAKES",
                emotion="urgency",
            ),
        ]
        strategy = {
            "story_one_liner": script.topic_title,
            "viewer_promise": "Accurate visual storytelling tied to research",
            "trust_tactics": ["Source lower-thirds", "Story-linked B-roll only"],
            "subscriber_hooks": ["Trust through specificity"],
            "avoid": ["Generic unrelated B-roll"],
        }

    package = VisualPackage(
        shot_list=shots,
        broll_prompts=broll,
        lower_thirds=lower,
        thumbnail_concepts=thumbs,
    )
    extras = {
        "creative_strategy": strategy,
        "verified_story_beats": beats,
        "on_screen_facts": on_screen_facts,
        "story_profile": profile,
        "grounding_news_hits": grounding.get("news_hits") or [],
        "retention_notes": [
            "Every shot has story_link — reject assets that could fit any random tech video",
            "Put dollar figures and court names in CapCut type, not AI text",
            f"Target ~{TARGET_SHOT_SECONDS:.0f}s visual pace for retention",
            "Prefer real news archive stills via news_search_query when available",
        ],
        "generate_queue": generate_queue[:PRIORITY_GENERATE_CAP],
        "editor_brand_kit": {
            "palette": "dark navy + cyan proof cards + white source type",
            "font_mood": "modern news sans",
            "end_screen": "Subscribe + next platform regulation video",
            "lower_third_pattern": "FACT on left · Source: outlet on right",
        },
        "uncertainty_flags": grounding.get("uncertainty_flags") or [],
    }
    return package, extras


def _package_markdown(package: VisualPackage, extras: dict[str, Any]) -> str:
    strat = extras.get("creative_strategy") or {}
    lines = [
        "# Visual Package — News-Grounded Creative Direction\n",
        f"**Story profile:** `{extras.get('story_profile')}`  ",
        f"**Shots:** {len(package.shot_list)} · **Prompts:** {len(package.broll_prompts)}\n",
        "## Creative strategy\n",
        f"- **One-liner:** {strat.get('story_one_liner', '')}",
        f"- **Viewer promise:** {strat.get('viewer_promise', '')}",
        "\n### Trust tactics\n",
    ]
    for t in strat.get("trust_tactics") or []:
        lines.append(f"- {t}")
    lines.append("\n### Avoid (credibility killers)\n")
    for t in strat.get("avoid") or []:
        lines.append(f"- {t}")

    lines.append("\n## Verified story beats (for CapCut fact cards)\n")
    for b in extras.get("verified_story_beats") or []:
        lines.append(
            f"- **{b.get('fact')}** — _{b.get('source_hint')}_ "
            f"({b.get('confidence')})"
        )

    lines.append("\n## On-screen facts\n")
    for f in extras.get("on_screen_facts") or []:
        lines.append(f"- {f.get('fact')} · Source: {f.get('source')}")

    lines.append("\n## Shot list (story-linked)\n")
    for s in package.shot_list:
        lines.append(
            f"- `{s.get('shot_id')}` [{s.get('section_id')}] "
            f"t={s.get('start_sec')}s **{s.get('type')}** — "
            f"{s.get('story_link')}"
        )
        if s.get("capcut_overlay"):
            lines.append(f"  - CapCut: `{s.get('capcut_overlay')}`")
        if s.get("source_lower_third"):
            lines.append(f"  - {s.get('source_lower_third')}")

    lines.append("\n## Story-specific Imagine / stock prompts\n")
    for b in package.broll_prompts:
        lines.append(f"### {b.get('shot_id')} — {b.get('story_link')}")
        lines.append(f"- News archive search: `{b.get('news_search_query')}`")
        lines.append(f"- Stock keywords: {', '.join(b.get('stock_keywords') or [])}")
        lines.append(f"- Prompt:\n\n> {b.get('prompt')}\n")

    lines.append("\n## Thumbnails (CapCut text only)\n")
    for t in package.thumbnail_concepts:
        lines.append(f"### {t.concept_id}: {t.headline}")
        lines.append(f"- Overlay: `{t.text_overlay}` · {t.emotion}")
        lines.append(f"- Imagine:\n\n> {t.visual_description}\n")

    lines.append("\n## Live news hits used for grounding\n")
    for h in (extras.get("grounding_news_hits") or [])[:12]:
        lines.append(f"- [{h.get('title','')}]({h.get('url','')}) — {h.get('snippet','')[:160]}")

    lines.append(
        "\n## Editor rules\n"
        "1. If a shot could appear in any random tech video, cut it.\n"
        "2. Never invent public-figure faces.\n"
        "3. Prefer licensed news stills when free/fair-use policy allows; AI fills gaps only.\n"
        "4. Fact cards must match latest reporting — dual-check $375m vs $567m phases.\n"
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

        log.info("Visual Director grounding visuals in live news + research")
        grounding = _gather_visual_grounding(script.topic_title, brief, ctx.settings)
        profile = _detect_story_profile(script.topic_title, grounding)
        log.info("Story profile: %s (news hits=%s)", profile, len(grounding.get("news_hits") or []))

        package, extras = _build_grounded_package(script, grounding, profile)

        # LLM elevates strategy when available — must stay story-grounded
        if llm_available(ctx.settings) or ctx.use_llm:
            try:
                payload = {
                    "script_meta": {
                        "title": script.title_working,
                        "topic": script.topic_title,
                        "runtime_min": script.estimated_runtime_minutes,
                        "sections": [
                            {
                                "id": s.id,
                                "title": s.title,
                                "start": s.start_timestamp,
                                "end": s.end_timestamp,
                                "excerpt": (s.narration or "")[:400],
                                "visual_cues": s.visual_cues,
                            }
                            for s in script.sections
                        ],
                    },
                    "research_brief": brief.model_dump(mode="json") if brief else None,
                    "grounding": grounding,
                    "story_profile": profile,
                    "baseline_strategy": extras.get("creative_strategy"),
                    "baseline_beats": extras.get("verified_story_beats"),
                    "instruction": (
                        "Improve and densify the visual plan. Keep every shot story-linked. "
                        "Correct dollar figures if news hits contradict the brief. "
                        "Never invent public-figure photoreal faces."
                    ),
                }
                data = chat_json(
                    SYSTEM,
                    json.dumps(payload, ensure_ascii=False, default=str)[:120000],
                    settings=ctx.settings,
                    temperature=0.35,
                    max_tokens=8192,
                )
                # Merge carefully: prefer LLM strategy/beats if present; keep dense baseline shots if LLM sparse
                if data.get("creative_strategy"):
                    extras["creative_strategy"] = data["creative_strategy"]
                if data.get("verified_story_beats"):
                    extras["verified_story_beats"] = data["verified_story_beats"]
                if data.get("on_screen_facts"):
                    extras["on_screen_facts"] = data["on_screen_facts"]
                if data.get("editor_brand_kit"):
                    extras["editor_brand_kit"] = data["editor_brand_kit"]
                if data.get("retention_notes"):
                    extras["retention_notes"] = data["retention_notes"] + extras.get(
                        "retention_notes", []
                    )[:2]
                llm_shots = data.get("shot_list") or []
                llm_broll = data.get("broll_prompts") or []
                if len(llm_shots) >= max(24, len(package.shot_list) // 3) and llm_broll:
                    thumbs = [
                        ThumbnailConcept.model_validate(t)
                        for t in (data.get("thumbnail_concepts") or [])
                    ] or package.thumbnail_concepts
                    for b in llm_broll:
                        b["prompt"] = _enrich_prompt(b.get("prompt") or "")
                        b.setdefault("story_link", b.get("story_link") or "story-linked")
                    package = VisualPackage(
                        shot_list=llm_shots,
                        broll_prompts=llm_broll,
                        lower_thirds=data.get("lower_thirds") or package.lower_thirds,
                        thumbnail_concepts=thumbs,
                    )
                    if data.get("generate_queue"):
                        extras["generate_queue"] = data["generate_queue"][
                            :PRIORITY_GENERATE_CAP
                        ]
                else:
                    log.warning(
                        "LLM visual plan too sparse or incomplete; keeping grounded baseline"
                    )
            except Exception as exc:  # noqa: BLE001
                log.warning("LLM visual elevation failed (%s); grounded baseline kept", exc)

        # Persist
        full = package.model_dump(mode="json")
        full["meta"] = extras
        ctx.store.write_json("visuals/package.json", full)
        ctx.store.write_text("visuals/package.md", _package_markdown(package, extras))
        ctx.store.write_json(
            "visuals/creative_strategy.json", extras.get("creative_strategy") or {}
        )
        ctx.store.write_json(
            "visuals/story_beats.json", extras.get("verified_story_beats") or []
        )

        queue_prompts = []
        by_id = {b.get("shot_id"): b for b in package.broll_prompts}
        for sid in extras.get("generate_queue") or []:
            if sid in by_id:
                queue_prompts.append(
                    {
                        "shot_id": sid,
                        "story_link": by_id[sid].get("story_link"),
                        "prompt": by_id[sid].get("prompt"),
                        "news_search_query": by_id[sid].get("news_search_query"),
                        "aspect_ratio": "16:9",
                        "priority": by_id[sid].get("priority"),
                    }
                )
        for t in package.thumbnail_concepts:
            queue_prompts.append(
                {
                    "shot_id": t.concept_id,
                    "kind": "thumbnail",
                    "prompt": t.visual_description,
                    "capcut_text_overlay": t.text_overlay,
                    "aspect_ratio": "16:9",
                    "priority": 1,
                }
            )
        ctx.store.write_json("visuals/imagine_queue.json", queue_prompts)
        ctx.store.write_text(
            "visuals/IMAGINE_PROMPTS.txt",
            "\n\n-----\n\n".join(
                f"[{q.get('shot_id')}] STORY: {q.get('story_link', '')}\n"
                f"NEWS SEARCH: {q.get('news_search_query', '')}\n"
                f"{q.get('prompt')}"
                for q in queue_prompts
            ),
        )

        log.info(
            "Visual Director done: profile=%s shots=%s prompts=%s",
            profile,
            len(package.shot_list),
            len(package.broll_prompts),
        )
        return mark_done(stage, {"visual_package": full})
    except Exception as exc:  # noqa: BLE001
        log.exception("Visual Director failed")
        return mark_failed(stage, str(exc))
