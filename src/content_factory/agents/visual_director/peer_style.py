"""Virtual Studio visual language — broadcast anchor with floating glass panels.

Reference look: football / sports-pundit virtual newsroom. Female anchor **Chloe**
stands center, controlling transparent holographic glass screens via a glass tablet.
Real logos, portraits, stats, and quotes live ON those panels — not as free-floating
CGI mush or empty documentary B-roll.

Channel badge: **Tech Frontier** (never SCENIUM or third-party watermarks).
Only ban AI-generator watermarks — logos and claim titles are required.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from config.settings import PROJECT_ROOT

STYLE_PATH = PROJECT_ROOT / "config" / "channel_visual_style.yaml"
STUDIO_REFERENCE_DIR = PROJECT_ROOT / "assets" / "studio_reference"
STUDIO_REFERENCE_BASE = STUDIO_REFERENCE_DIR / "chloe_studio_base.jpg"
STUDIO_REFERENCE_LOGO_PANEL = STUDIO_REFERENCE_DIR / "chloe_studio_logo_panel.jpg"

# Permanent identity lock for every generative still
STYLE_LOCK = (
    "Ultra-detailed cinematic photorealism, futuristic virtual newsroom studio. "
    "Consistent female anchor Chloe: shoulder-length pink-blonde hair, white t-shirt, "
    "dark jeans, professional broadcast presence, perfect facial consistency across shots. "
    "She stands center holding a transparent glass tablet used to control the environment. "
    "Background: massive glowing cyan tech globe, digital matrix walls, curved teal sofa. "
    "Floating transparent glass panels surround her displaying data, portraits, logos, and quotes. "
    "Upper-right corner: Tech Frontier channel logo badge (not SCENIUM). "
    "8k broadcast quality, YouTube 16:9. NO AI generator watermark, NO stock watermark."
)

CHANNEL_BADGE = "Tech Frontier"


def studio_reference_paths() -> dict[str, Path]:
    """Canonical Chloe studio plates for image-to-image consistency."""
    return {
        "base": STUDIO_REFERENCE_BASE,
        "logo_panel": STUDIO_REFERENCE_LOGO_PANEL,
        "dir": STUDIO_REFERENCE_DIR,
    }


def studio_reference_manifest() -> dict[str, Any]:
    """Paths + policy for editors and generation tools."""
    paths = studio_reference_paths()
    return {
        "policy": (
            "Use chloe_studio_base.jpg as the primary image-edit reference for all "
            "subsequent Virtual Studio stills. Keep Chloe face, wardrobe, and set; "
            "change only floating glass panel content and minor pose."
        ),
        "primary": "base",
        "files": {
            "base": {
                "path": str(paths["base"]),
                "relative": "assets/studio_reference/chloe_studio_base.jpg",
                "exists": paths["base"].exists(),
                "use": "Primary base plate for image_edit / Gemini reference-first",
            },
            "logo_panel": {
                "path": str(paths["logo_panel"]),
                "relative": "assets/studio_reference/chloe_studio_logo_panel.jpg",
                "exists": paths["logo_panel"].exists(),
                "use": "Secondary plate when beat is logo sting",
            },
        },
    }


def load_visual_style() -> dict[str, Any]:
    if not STYLE_PATH.exists():
        return {}
    with STYLE_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def style_lock() -> str:
    return STYLE_LOCK


def title_block(main: str, sub: str = "") -> str:
    """Typography burned into a floating transparent glass panel."""
    main = main.strip().upper()
    sub = sub.strip().upper()
    if sub:
        return (
            f"Inside a floating transparent glass panel: primary line '{main}' in bright "
            f"cyan/amber, secondary line '{sub}' in clean white, highly readable, sharp edges."
        )
    return (
        f"Inside a floating transparent glass panel: '{main}' in glowing cyan/amber text, "
        f"highly readable, sharp edges."
    )


def logo_block(company: str, local_script: str = "") -> str:
    """On-image brand presence on a glass panel (not free-floating mush)."""
    extra = (
        f" Also show sharp '{local_script}' lettering on a holographic glass chip."
        if local_script
        else ""
    )
    return (
        f"A sharp, official-looking {company} logo displayed clearly on a floating "
        f"transparent glass screen behind or beside the anchor."
        f"{extra}"
    )


def anchor_chloe(action: str) -> str:
    return (
        f"Female anchor Chloe (pink-blonde hair, white shirt, dark jeans) holding a "
        f"transparent tablet, {action}, in a premium virtual newsroom with teal sofa "
        f"and glowing cyan globe background."
    )


def hero_robot(action: str) -> str:
    """Legacy helper: robot content appears as a *panel feed*, not a full-frame CGI hero."""
    return (
        f"On a large floating glass panel beside Chloe: sleek white-and-black humanoid robot "
        f"with cyan eye sensors, {action}, photoreal CGI feed framed in holographic borders."
    )


# Story-agnostic cinematic library — always Chloe + glass panels
CINEMATIC_LIBRARY: dict[str, list[str]] = {
    "ai_model": [
        "Chloe expanding a floating holographic glass panel showing a massive neural network diagram",
        "Chloe gesturing toward a floating screen of glowing server racks and AI processing chips",
        "Chloe reading a semi-transparent panel comparing two glowing model-size data charts",
        "Chloe swiping her tablet as a giant glass panel reveals a parameter-count explosion of light",
    ],
    "coding_agent": [
        "Chloe swiping her glass tablet, bringing up a glowing transparent window of cascading source code",
        "Chloe beside a floating glass panel showing a repository file tree connecting in real time",
        "Chloe pointing her tablet at a monorepo hologram of millions of glowing file nodes",
        "Chloe presenting a dual-panel IDE feed: search results left, generated code right",
    ],
    "china_tech": [
        "Chloe in the virtual studio, a massive transparent panel displaying Asian tech market graphs and neon city data",
        "Chloe gesturing to a floating screen of international user-growth metrics over a globe",
        "Chloe presenting a glass panel with ByteDance / TikTok-scale infrastructure holograms",
    ],
    "legal_meta": [
        "Chloe holding her tablet while a floating glass panel shows scales-of-justice over tech branding",
        "Chloe looking at a transparent screen with a legal document snapshot in glowing borders",
        "Chloe presenting dual glass panels: company logo left, court/AG portrait right",
    ],
    "money_stakes": [
        "Chloe in the studio, floating glass panels surging with financial charts and currency metrics",
        "Chloe tapping her tablet as a glass panel slams a giant penalty or valuation number into view",
    ],
    "robotics": [
        "Chloe presenting a glass panel video feed of a humanoid robot walking a factory floor",
        "Chloe beside a floating panel showing robot hands assembling a precision component",
    ],
}


def cinematic_for_topic(topic: str) -> list[str]:
    t = topic.lower()
    out: list[str] = []
    if any(k in t for k in ("muse", "codebase", "coding", "agent", "copilot", "devtools")):
        out.extend(CINEMATIC_LIBRARY["coding_agent"])
        out.extend(CINEMATIC_LIBRARY["ai_model"])
    if any(k in t for k in ("ai", "model", "parameter", "llm", "gpt", "qwen", "kimi", "trillion")):
        out.extend(CINEMATIC_LIBRARY["ai_model"])
        out.extend(CINEMATIC_LIBRARY["china_tech"])
    if any(k in t for k in ("meta", "facebook", "instagram", "nuisance", "court", "ruling")):
        out.extend(CINEMATIC_LIBRARY["legal_meta"])
        out.extend(CINEMATIC_LIBRARY["money_stakes"])
        out.extend(CINEMATIC_LIBRARY["coding_agent"])
    if any(k in t for k in ("bytedance", "byte-dance", "tiktok", "douyin", "seedance")):
        out.extend(CINEMATIC_LIBRARY["china_tech"])
        out.extend(CINEMATIC_LIBRARY["ai_model"])
    if any(k in t for k in ("robot", "humanoid", "tesla bot", "optimus", "figure ai")):
        out.extend(CINEMATIC_LIBRARY["robotics"])
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
    """Full Imagine/Gemini prompt: Chloe studio shell + claim panels + logo."""
    # If scene already describes Chloe, don't double-wrap; else frame as studio action
    scene_l = scene.lower()
    if "chloe" in scene_l:
        framed = scene.rstrip(".") + "."
    else:
        framed = (
            f"{anchor_chloe('presenting the story on floating glass panels')}. "
            f"Primary glass panel content: {scene.rstrip('.')}. "
        )
    parts = [
        framed,
        logo_block(company, logo_local),
        title_block(main_title, sub_title),
        extra,
        STYLE_LOCK,
        "Composition: Chloe center or center-left; giant glass panel with typography and brand "
        "on the opposite side; Tech Frontier badge top-right; rich studio depth.",
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
                    "Background plate: Chloe in the virtual studio",
                    "Composite a floating transparent glass panel effect",
                    "Place text inside the glass panel: bold white/cyan",
                    "Add company logo chip to the top of the glass frame",
                    "Source footer 18pt bottom-left of the glass frame",
                    "Animate glass panel sliding in (0.4s) while Chloe interacts with tablet",
                ],
                "audio_hit": "hologram whoosh + soft glass chime",
                "when": f.get("when") or f.get("beat") or "hook",
            }
        )
    recipes.append(
        {
            "id": "mg_compare_01",
            "type": "comparison_card",
            "on_screen_text": "Before vs After / Model A vs B",
            "capcut_steps": [
                "Generate two floating transparent glass panels flanking Chloe",
                "Place logos of each side into respective panels",
                "Big numbers glowing on glass; cyan vs amber accents",
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
            "action": (
                "Screenshot top reputable article — composite into a floating transparent "
                "glass panel next to Chloe (prefer black-on-black article layout with source chip)"
            ),
            "url_hint": (news_hits[0].get("url") if news_hits else ""),
            "capcut": "Panel drifts slightly; red highlight box tracks on key sentence",
            "priority": 1,
        },
        {
            "id": "sc_second_source",
            "type": "ui_screen",
            "action": "Second independent outlet confirming the claim — dual glass panels",
            "url_hint": (news_hits[1].get("url") if len(news_hits) > 1 else ""),
            "capcut": "Two glass panels flanking Chloe; trust layout",
            "priority": 1,
        },
        {
            "id": "sc_official",
            "type": "ui_screen",
            "action": f"Official product/company page for: {topic[:80]}",
            "capcut": "Glass panel scales up as Chloe points with tablet",
            "priority": 1,
        },
    ]
