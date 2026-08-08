"""AI Revolution–class visual language — cinematic CGI with logos + burned titles.

Reference look: humanoid AI/robot in server hall, holographic UI, company brand
signage, GIGANTIC claim text (e.g. ByteDance / 10 TRILLION PARAMETERS).
Only ban AI-generator watermarks — logos and titles are required where they matter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config.settings import PROJECT_ROOT

STYLE_PATH = PROJECT_ROOT / "config" / "channel_visual_style.yaml"

STYLE_LOCK = (
    "Ultra-detailed cinematic 3D CGI, Unreal Engine 5 quality, volumetric blue and cyan "
    "light, reflective materials, dense server racks with multicolored cable rainbows and "
    "LED status lights, floating holographic HUD with neural network graphs, dramatic rim "
    "lighting, shallow depth of field, YouTube 16:9, premium AI news commercial aesthetic. "
    "NO AI generator watermark, NO stock photo watermark, NO blurry mush logos."
)


def load_visual_style() -> dict[str, Any]:
    if not STYLE_PATH.exists():
        return {}
    with STYLE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def style_lock() -> str:
    return STYLE_LOCK


def title_block(main: str, sub: str = "") -> str:
    """Instruction for burned-in typography like the ByteDance reference."""
    main = main.strip().upper()
    sub = sub.strip().upper()
    if sub:
        return (
            f"Large bold sans-serif 3D/neon typography on the right or lower-right third: "
            f'primary line "{main}" in bright white-to-amber gradient, secondary line '
            f'"{sub}" in clean white, crisp edges, highly readable at small size, '
            f"perfect kerning, no spelling errors."
        )
    return (
        f"Large bold sans-serif 3D/neon typography: \"{main}\" in bright white-to-amber "
        f"gradient, crisp, highly readable, no spelling errors."
    )


def logo_block(company: str, local_script: str = "") -> str:
    """On-image brand presence."""
    extra = f" Also include sharp {local_script} lettering on a holographic sign." if local_script else ""
    return (
        f"Clearly visible, sharp, correct-looking {company} logo and brand mark in-frame "
        f"(holographic sign, wall badge, or HUD corner) — official colors, not abstract mush."
        f"{extra}"
    )


def hero_robot(action: str) -> str:
    return (
        f"Sleek white-and-black humanoid robot with glowing cyan eye sensors, "
        f"{action}, photoreal CGI materials, premium sci-fi product hero."
    )


# Story-agnostic cinematic library (always logo+title ready via wrappers)
CINEMATIC_LIBRARY: dict[str, list[str]] = {
    "ai_model": [
        "Humanoid robot in dense blue server hall holding a holographic neural tablet",
        "Robot silhouette before towering GPU racks with volumetric cyan god rays",
        "Close hero robot face reflecting server LEDs, holographic brain graph floating",
        "Dual-world energy: robot between warm Silicon Valley night and neon Asia skyline",
    ],
    "coding_agent": [
        "Humanoid robot at a multi-monitor coding fortress, holographic code panes",
        "Robot pointing into a translucent monorepo tree hologram of glowing nodes",
        "Agent robot walking a corridor of server cages pulling a light-thread of code",
        "Robot and floating IDE hologram over a dark glass floor reflecting LEDs",
    ],
    "china_tech": [
        "Robot under a glowing Chinese mega-city tech brand hologram in a server cathedral",
        "Cinematic server hall with neon Chinese corporate signage and holographic dashboards",
        "Humanoid AI inspecting a holographic tablet labeled with the company product name",
    ],
    "legal_meta": [
        "Robot holding scales-of-justice hologram inside a blue-lit data center (tech-law hybrid)",
        "Server hall with Meta-style brand hologram and bold penalty-claim typography space",
        "Robot facing a wall of social-app color light (no illegible mush) plus brand logo badge",
    ],
    "money_stakes": [
        "Robot presenting a holographic coin-stack and chart explosion of light (no tiny unreadable digits except the main title)",
        "Vault-like server cage doors open, robot stepping out with glowing contract hologram",
    ],
}


def cinematic_for_topic(topic: str) -> list[str]:
    t = topic.lower()
    out: list[str] = []
    if any(k in t for k in ("muse", "codebase", "coding", "agent", "copilot", "devtools")):
        out.extend(CINEMATIC_LIBRARY["coding_agent"])
        out.extend(CINEMATIC_LIBRARY["ai_model"])
    if any(k in t for k in ("ai", "model", "parameter", "llm", "gpt", "qwen", "kimi")):
        out.extend(CINEMATIC_LIBRARY["ai_model"])
        out.extend(CINEMATIC_LIBRARY["china_tech"])
    if any(k in t for k in ("meta", "facebook", "instagram", "nuisance", "court", "ruling")):
        out.extend(CINEMATIC_LIBRARY["legal_meta"])
        out.extend(CINEMATIC_LIBRARY["money_stakes"])
        out.extend(CINEMATIC_LIBRARY["coding_agent"])
    if any(k in t for k in ("bytedance", "byte-dance", "tiktok", "douyin")):
        out.extend(CINEMATIC_LIBRARY["china_tech"])
        out.extend(CINEMATIC_LIBRARY["ai_model"])
    if not out:
        out = CINEMATIC_LIBRARY["ai_model"] + CINEMATIC_LIBRARY["coding_agent"]
    return out


def build_gemini_prompt(
    *,
    scene: str,
    company: str,
    main_title: str,
    sub_title: str = "",
    logo_local: str = "",
    extra: str = "",
) -> str:
    """Full Gemini/Imagine prompt matching the ByteDance reference aesthetic."""
    parts = [
        scene.rstrip(".") + ".",
        hero_robot("standing in three-quarter view, interacting with a holographic interface")
        if "robot" not in scene.lower()
        else "",
        logo_block(company, logo_local),
        title_block(main_title, sub_title),
        extra,
        STYLE_LOCK,
        "Composition: subject on one side, giant typography dominating the opposite side, "
        "holographic brand sign upper area, rich server-room depth, Instagram/YouTube thumbnail punch.",
    ]
    return " ".join(p for p in parts if p)


def motion_graphic_recipes(facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recipes = []
    for i, f in enumerate(facts[:12]):
        recipes.append(
            {
                "id": f"mg_{i+1:02d}",
                "type": "kinetic_stat",
                "on_screen_text": f.get("fact", "")[:100],
                "source_footer": f.get("source", "Source"),
                "capcut_steps": [
                    "Full-bleed dark navy / server blue background",
                    "Number or claim in 120–160pt bold white/amber",
                    "Company logo chip top-left",
                    "Count-up or slam-in animation 0.4s",
                    "Source footer 18pt bottom-left",
                    "Hold 2.5–4s then whip to next",
                ],
                "audio_hit": "whoosh + soft impact",
                "when": f.get("when") or f.get("beat") or "hook",
            }
        )
    recipes.append(
        {
            "id": "mg_compare_01",
            "type": "comparison_card",
            "on_screen_text": "Before vs After / Model A vs B",
            "capcut_steps": [
                "Two panels 50/50 with logos of each side if companies differ",
                "Big numbers; cyan vs amber accents",
            ],
            "when": "benchmarks_demos",
        }
    )
    return recipes


def screen_capture_plan(topic: str, news_hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "id": "sc_primary_article",
            "type": "ui_screen",
            "action": "Screenshot top reputable article — crop ads, keep outlet masthead visible",
            "url_hint": (news_hits[0].get("url") if news_hits else ""),
            "capcut": "Ken Burns + red highlight box on key sentence",
            "priority": 1,
        },
        {
            "id": "sc_second_source",
            "type": "ui_screen",
            "action": "Second independent outlet confirming the claim",
            "url_hint": (news_hits[1].get("url") if len(news_hits) > 1 else ""),
            "capcut": "Side-by-side trust layout",
            "priority": 1,
        },
        {
            "id": "sc_official",
            "type": "ui_screen",
            "action": f"Official product/company page for: {topic[:80]}",
            "capcut": "Zoom on product name + date",
            "priority": 1,
        },
    ]
