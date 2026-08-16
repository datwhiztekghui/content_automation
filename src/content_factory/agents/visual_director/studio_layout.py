"""Virtual News Studio spatial layout + video-feed rules.

Chloe is the constant on-camera presence. Story content (logos, portraits, stats,
article screenshots, product UI, CGI metaphors) lives on **floating glass panels**
and **video-feed plates** — never as orphan full-frame stock with no studio shell.

Brand: AIInfoRoom (upper-right badge). Never leave SCENIUM or third-party marks.
"""

from __future__ import annotations

from typing import Any

# Permanent set design (matches STYLE_LOCK / reference stills)
SET_DESIGN: dict[str, str] = {
    "anchor": "Chloe — pink-blonde shoulder-length hair, white t-shirt, dark jeans",
    "prop": "transparent glass tablet in Chloe's hands (always present)",
    "background": "glowing cyan tech globe + digital matrix walls",
    "furniture": "curved teal sofa mid-ground",
    "channel_badge": "AIInfoRoom logo — upper-right corner, every generative still",
    "grade": "broadcast cyan / teal / near-black, high contrast",
}

# Named panel slots (editor + prompt vocabulary)
PANEL_SLOTS: dict[str, dict[str, str]] = {
    "hero_right": {
        "position": "right two-thirds, slightly behind Chloe",
        "size": "large (primary claim / hero image)",
        "use": "kinetic stats, mega titles, primary product or portrait",
    },
    "hero_left": {
        "position": "left third beside Chloe",
        "size": "medium-large",
        "use": "secondary claim, comparison left side, supporting portrait",
    },
    "dual_flank": {
        "position": "symmetric left + right of Chloe",
        "size": "medium pair",
        "use": "A vs B comparisons, logo vs logo, before/after",
    },
    "tablet_mirror": {
        "position": "reflected on Chloe's glass tablet surface",
        "size": "small readable detail",
        "use": "echo of main panel content for interactivity",
    },
    "lower_strip": {
        "position": "lower third of frame, glass bar",
        "size": "wide thin",
        "use": "source footer, soft lower-third name/role",
    },
    "video_feed": {
        "position": "large panel (usually hero_right) as live video plate",
        "size": "large",
        "use": "product demo, robot walk, UI screen recording, news clip",
    },
}

# Asset class → default panel mapping
ASSET_TO_PANEL: dict[str, str] = {
    "kinetic_stat": "hero_right",
    "news_headline": "hero_right",
    "comparison_card": "dual_flank",
    "logo_card": "hero_right",
    "person_plate": "hero_right",
    "proof_quote": "hero_right",
    "ui_screen": "video_feed",
    "cinematic_broll": "video_feed",
    "geo_map": "hero_right",
    "timeline": "hero_right",
    "end_brand": "hero_right",
}

# Black-on-black article / proof-card template (peer article stills)
ARTICLE_LAYOUT: dict[str, Any] = {
    "name": "black_on_black_source_card",
    "background": "near-black (#0a0a0f) with subtle cyan edge glow",
    "headline": "bold white / cyan, 2–8 words max for on-panel claim",
    "body_snippet": "muted light gray, 1–2 lines only",
    "source_chip": {
        "placement": "top-left or bottom-left of glass panel",
        "style": "rounded pill: outlet name + optional date",
        "examples": ["BBC NEWS", "THE VERGE", "OFFICIAL BLOG", "REUTERS"],
    },
    "logo_chip": "company mark top-right of the glass panel interior",
    "do_not": [
        "full-bleed white newsprint with tiny unreadable body text",
        "AI-invented fake newspaper mastheads",
        "source-less claim cards when a real outlet exists",
    ],
}

# Video-feed rules (when panel shows motion / demo / robot / UI)
VIDEO_FEED_RULES: list[str] = [
    "Treat product demos, robot motion, and UI recordings as VIDEO FEEDS inside glass panels — not full-frame takeover that loses Chloe.",
    "Keep Chloe visible on at least one side or as a medium shot; panel can dominate but studio shell remains.",
    "Hook cuts 2–4s; body 4–7s; whip panel content on VO beats.",
    "When VO names a company → logo_card panel within 1–2s.",
    "When VO names a CEO/public figure → person_plate with REAL captured photo on glass.",
    "When VO cites a number → kinetic_stat on glass with source footer.",
    "Never invent photoreal faces for real people; capture first, optional reference-first grade only.",
    "Only ban AI-generator watermarks — logos and burned claim titles stay.",
]

SPATIAL_COMPOSITION_RULES: list[str] = [
    "Chloe center or center-left; never crop her out of generative hero frames.",
    "Glass panels float with slight parallax; cyan edge light; subtle transparency.",
    "Max 1–2 primary panels in focus; avoid cluttered HUD soup.",
    "AIInfoRoom badge always upper-right on generative stills.",
    "Tablet interaction: Chloe swipes/taps to 'change' panel content between shots.",
    "Thumbnails: Chloe + one giant glass panel with mega text + real logo/face assets.",
]


def panel_for_asset(asset_class: str) -> dict[str, str]:
    slot = ASSET_TO_PANEL.get(asset_class, "hero_right")
    meta = PANEL_SLOTS.get(slot, PANEL_SLOTS["hero_right"])
    return {"slot": slot, **meta}


def studio_prompt_suffix(asset_class: str = "cinematic_broll") -> str:
    """Append to generative prompts so layout stays consistent."""
    panel = panel_for_asset(asset_class)
    return (
        f" Layout: Chloe in virtual newsroom; content on floating glass panel "
        f"({panel['slot']}: {panel['position']}). AIInfoRoom badge top-right. "
        f"No SCENIUM mark. No AI watermark."
    )


def article_card_prompt(
    claim: str,
    source: str = "Source",
    company: str = "",
) -> str:
    """Prompt / CapCut recipe for black-on-black proof cards on glass."""
    logo = f" Include sharp {company} logo chip on the panel." if company else ""
    return (
        f"Black-on-black glass article card inside a floating transparent panel: "
        f"bold claim '{claim[:80]}', source chip '{source.upper()[:40]}' bottom-left, "
        f"subtle cyan edge glow, near-black field, highly readable."
        f"{logo}"
    )


def studio_layout_manifest() -> dict[str, Any]:
    """Writable artifact for editors and downstream tools."""
    return {
        "format": "virtual_news_studio",
        "anchor": "Chloe",
        "channel_badge": "AIInfoRoom",
        "set_design": SET_DESIGN,
        "panel_slots": PANEL_SLOTS,
        "asset_to_panel": ASSET_TO_PANEL,
        "article_layout": ARTICLE_LAYOUT,
        "video_feed_rules": VIDEO_FEED_RULES,
        "spatial_composition_rules": SPATIAL_COMPOSITION_RULES,
        "capcut_stack": [
            "Layer 0: studio plate (Chloe + globe + sofa) or generative still",
            "Layer 1: floating glass panel PNG/effect",
            "Layer 2: real logo / real portrait / screenshot / kinetic type inside panel",
            "Layer 3: source chip + optional lower-third",
            "Layer 4: AIInfoRoom badge (upper-right) if not burned in",
        ],
    }
