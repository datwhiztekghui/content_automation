"""AI Revolution–class visual language helpers (competitive faceless tech news)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config.settings import PROJECT_ROOT

STYLE_PATH = PROJECT_ROOT / "config" / "channel_visual_style.yaml"


def load_visual_style() -> dict[str, Any]:
    if not STYLE_PATH.exists():
        return {}
    with STYLE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


# Cinematic tech prompts that match high-retention AI news channels
# (energy + specificity — not empty rooms)
CINEMATIC_LIBRARY: dict[str, list[str]] = {
    "ai_model": [
        "Cinematic ultra-wide of a dark GPU cluster hall with volumetric cyan light beams between racks, particles in air, futuristic but photoreal data center at night, no logos no text no watermark",
        "Abstract photoreal neural network as glowing glass filaments in black void, camera slow orbit, high-end tech commercial, no text no logos",
        "Close-up of liquid metal forming a brain-like lattice under cool studio lights, sci-fi product film still, photoreal, no text no watermark",
        "Split-screen energy: left warm Silicon Valley night skyline, right neon Shanghai skyline, dual world AI race mood, photoreal, no logos no text",
    ],
    "china_tech": [
        "Cinematic night aerial of a modern Chinese megacity CBD with LED towers and traffic light trails, cyber documentary grade, no readable billboards, no logos",
        "Photoreal R&D cleanroom with engineers in bunny suits around wafer equipment, cool white light, Chinese tech industrial scale, faces unrecognizable, no logos",
        "High-speed rail blur past a futuristic Chinese tech park at dusk, motion energy, photoreal, no text no logos",
    ],
    "legal_meta": [
        "Cinematic low-angle of a modern glass courthouse at blue hour with press camera flashes as bokeh orbs, high-stakes news open, no readable signs no logos",
        "Dark sleek motion-graphic desk with holographic scale-of-justice silhouette made of light only (no metal prop cliché), premium tech-news brand frame, no text",
        "Macro of smartphone glass reflecting abstract Instagram-like color gradients only (no UI icons), parent silhouette soft background, youth-safety stakes, no logos",
    ],
    "money_stakes": [
        "Cinematic abstract: cascading translucent digits dissolving into dust over a dark city, high-end fintech commercial still, NO legible numbers, no logos",
        "Photoreal vault door barely open with cold light spilling out, stakes and consequence mood, no text no logos",
    ],
    "product_ui_safe": [
        "Photoreal over-shoulder laptop in dark room, monitor showing only abstract code rain and soft graphs with no legible text, hacker-news aesthetic, no logos",
        "Clean dark UI mock environment with empty panels and neon dividers ready for editor to drop real screenshots, 3D-ish but photoreal, no brand marks",
    ],
}


def cinematic_for_topic(topic: str) -> list[str]:
    t = topic.lower()
    out: list[str] = []
    if any(k in t for k in ("ai", "model", "parameter", "llm", "gpt", "qwen", "kimi")):
        out.extend(CINEMATIC_LIBRARY["ai_model"])
        out.extend(CINEMATIC_LIBRARY["china_tech"])
    if any(k in t for k in ("meta", "facebook", "instagram", "nuisance", "court", "ruling")):
        out.extend(CINEMATIC_LIBRARY["legal_meta"])
        out.extend(CINEMATIC_LIBRARY["money_stakes"])
    if not out:
        out = (
            CINEMATIC_LIBRARY["ai_model"]
            + CINEMATIC_LIBRARY["product_ui_safe"]
            + CINEMATIC_LIBRARY["money_stakes"]
        )
    return out


def motion_graphic_recipes(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """CapCut / AE recipes — this is what peer channels win with."""
    recipes = []
    for i, f in enumerate(facts[:12]):
        recipes.append(
            {
                "id": f"mg_{i+1:02d}",
                "type": "kinetic_stat",
                "on_screen_text": f.get("fact", "")[:100],
                "source_footer": f.get("source", "Source"),
                "capcut_steps": [
                    "Full-bleed dark navy background",
                    "Number or claim in 120–160pt bold white/cyan",
                    "Count-up or slam-in animation 0.4s",
                    "Source footer 18pt bottom-left: Source · outlet",
                    "Hold 2.5–4s then whip to next",
                ],
                "audio_hit": "subtle whoosh + soft impact on slam",
                "when": f.get("when") or f.get("beat") or "hook",
            }
        )
    recipes.append(
        {
            "id": "mg_compare_01",
            "type": "comparison_card",
            "on_screen_text": "Before vs After / Phase 1 vs Phase 2",
            "capcut_steps": [
                "Two vertical panels 50/50",
                "Left label PHASE 1 / Right PHASE 2",
                "Big numbers only; editor fills verified amounts",
                "Accent line cyan left, amber right",
            ],
            "when": "benchmarks_demos",
        }
    )
    recipes.append(
        {
            "id": "mg_timeline_01",
            "type": "timeline",
            "on_screen_text": "Release → Ruling → Appeal",
            "capcut_steps": [
                "Horizontal timeline with 3 nodes",
                "Active node pulses cyan",
                "Pop labels as VO hits each beat",
            ],
            "when": "bigger_picture",
        }
    )
    return recipes


def screen_capture_plan(topic: str, news_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Real proof assets peer channels use constantly."""
    plan = [
        {
            "id": "sc_primary_article",
            "type": "ui_screen",
            "action": "Screenshot top reputable article (BBC/Reuters/AP/court) — crop ads",
            "url_hint": (news_hits[0].get("url") if news_hits else ""),
            "capcut": "Ken Burns slow zoom; red box highlight on key sentence",
            "priority": 1,
        },
        {
            "id": "sc_second_source",
            "type": "ui_screen",
            "action": "Second independent outlet confirming the number",
            "url_hint": (news_hits[1].get("url") if len(news_hits) > 1 else ""),
            "capcut": "Side-by-side with first source for trust",
            "priority": 1,
        },
        {
            "id": "sc_official",
            "type": "ui_screen",
            "action": f"Official page related to: {topic[:80]} (AG site, company blog, arXiv, GitHub)",
            "capcut": "Cursor-free; zoom on title and date",
            "priority": 1,
        },
    ]
    return plan
