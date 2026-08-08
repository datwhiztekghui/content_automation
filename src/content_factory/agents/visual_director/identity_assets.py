"""Identity assets: real logos + real public-figure photos for news authenticity.

Peer channels show the company and the person. We plan CAPTURE (official/news
sources), not invented deepfakes. Optional reference-first Imagine only after
a real photo is on disk.
"""

from __future__ import annotations

import re
from typing import Any

# Topic keywords → entities the editor MUST put on screen
ENTITY_CATALOG: list[dict[str, Any]] = [
    {
        "keys": ["meta", "facebook", "instagram", "threads", "muse code", "whatsapp"],
        "company": "Meta",
        "products": ["Meta", "Facebook", "Instagram"],
        "people": [
            {
                "name": "Mark Zuckerberg",
                "role": "CEO, Meta",
                "search": "Mark Zuckerberg official portrait Meta",
            }
        ],
        "logo_search": [
            "Meta logo official transparent PNG",
            "Meta newsroom brand assets",
        ],
    },
    {
        "keys": ["openai", "chatgpt", "gpt-4", "gpt-5", "sora", "astra"],
        "company": "OpenAI",
        "products": ["OpenAI", "ChatGPT"],
        "people": [
            {
                "name": "Sam Altman",
                "role": "CEO, OpenAI",
                "search": "Sam Altman official portrait",
            }
        ],
        "logo_search": ["OpenAI logo official"],
    },
    {
        "keys": ["anthropic", "claude"],
        "company": "Anthropic",
        "products": ["Anthropic", "Claude"],
        "people": [
            {
                "name": "Dario Amodei",
                "role": "CEO, Anthropic",
                "search": "Dario Amodei official portrait",
            }
        ],
        "logo_search": ["Anthropic logo official"],
    },
    {
        "keys": ["google", "deepmind", "gemini", "alphabet", "wayland"],
        "company": "Google",
        "products": ["Google", "Gemini", "DeepMind"],
        "people": [
            {
                "name": "Sundar Pichai",
                "role": "CEO, Alphabet/Google",
                "search": "Sundar Pichai official portrait",
            },
            {
                "name": "Demis Hassabis",
                "role": "CEO, Google DeepMind",
                "search": "Demis Hassabis official portrait",
            },
        ],
        "logo_search": ["Google logo official", "DeepMind logo"],
    },
    {
        "keys": ["microsoft", "openai partnership", "copilot", "azure"],
        "company": "Microsoft",
        "products": ["Microsoft", "Copilot", "Azure"],
        "people": [
            {
                "name": "Satya Nadella",
                "role": "CEO, Microsoft",
                "search": "Satya Nadella official portrait",
            }
        ],
        "logo_search": ["Microsoft logo official"],
    },
    {
        "keys": ["nvidia", "blackwell", "cuda", "jensen"],
        "company": "NVIDIA",
        "products": ["NVIDIA", "CUDA"],
        "people": [
            {
                "name": "Jensen Huang",
                "role": "CEO, NVIDIA",
                "search": "Jensen Huang official portrait",
            }
        ],
        "logo_search": ["NVIDIA logo official"],
    },
    {
        "keys": ["xai", "grok", "elon"],
        "company": "xAI",
        "products": ["xAI", "Grok"],
        "people": [
            {
                "name": "Elon Musk",
                "role": "CEO, xAI / Tesla",
                "search": "Elon Musk official portrait",
            }
        ],
        "logo_search": ["xAI logo official"],
    },
    {
        "keys": ["apple", "iphone", "tim cook"],
        "company": "Apple",
        "products": ["Apple"],
        "people": [
            {
                "name": "Tim Cook",
                "role": "CEO, Apple",
                "search": "Tim Cook official portrait",
            }
        ],
        "logo_search": ["Apple logo official"],
    },
    {
        "keys": ["alibaba", "qwen"],
        "company": "Alibaba",
        "products": ["Alibaba", "Qwen"],
        "people": [
            {
                "name": "Eddie Wu",
                "role": "CEO, Alibaba",
                "search": "Eddie Wu Alibaba CEO portrait",
            }
        ],
        "logo_search": ["Alibaba logo official", "Qwen logo"],
    },
    {
        "keys": ["new mexico", "torrez", "public nuisance", "biedscheid"],
        "company": "Meta",  # defendant in that story
        "products": ["Meta", "Instagram", "Facebook"],
        "people": [
            {
                "name": "Mark Zuckerberg",
                "role": "CEO, Meta",
                "search": "Mark Zuckerberg Meta CEO photo",
            },
            {
                "name": "Raúl Torrez",
                "role": "Attorney General, New Mexico",
                "search": "Raul Torrez New Mexico Attorney General official photo",
            },
            {
                "name": "Bryan Biedscheid",
                "role": "Judge, New Mexico",
                "search": "Judge Bryan Biedscheid New Mexico",
            },
        ],
        "logo_search": [
            "Meta logo official",
            "New Mexico state seal official",
            "New Mexico Attorney General logo",
        ],
    },
]


def extract_entities(topic: str, extra_text: str = "") -> list[dict[str, Any]]:
    """Match topic/research text to known companies and people."""
    blob = f"{topic} {extra_text}".lower()
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for entry in ENTITY_CATALOG:
        if any(k in blob for k in entry["keys"]):
            key = entry["company"]
            if key in seen:
                # merge people if same company hit twice
                for f in found:
                    if f["company"] == key:
                        names = {p["name"] for p in f["people"]}
                        for p in entry["people"]:
                            if p["name"] not in names:
                                f["people"].append(p)
                        break
                continue
            seen.add(key)
            found.append(
                {
                    "company": entry["company"],
                    "products": list(entry["products"]),
                    "people": list(entry["people"]),
                    "logo_search": list(entry["logo_search"]),
                }
            )
    # Heuristic: "CEO Name" patterns not in catalog
    for m in re.finditer(
        r"\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){1,2})\b(?:\s*,\s*|\s+)(?:CEO|founder|CTO)",
        f"{topic} {extra_text}",
    ):
        name = m.group(1)
        if not any(name in p["name"] for e in found for p in e["people"]):
            found.append(
                {
                    "company": "Unknown",
                    "products": [],
                    "people": [
                        {
                            "name": name,
                            "role": "Named executive",
                            "search": f"{name} official portrait",
                        }
                    ],
                    "logo_search": [],
                }
            )
    return found


def build_identity_capture_plan(
    topic: str,
    entities: list[dict[str, Any]],
    news_hits: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Editor + pipeline checklist: capture real logos and real faces."""
    logos: list[dict[str, Any]] = []
    people: list[dict[str, Any]] = []
    for ent in entities:
        for i, q in enumerate(ent.get("logo_search") or []):
            logos.append(
                {
                    "id": f"logo_{ent['company'].lower().replace(' ', '_')}_{i}",
                    "company": ent["company"],
                    "product": (ent.get("products") or [ent["company"]])[0],
                    "capture_method": "download_official_or_screenshot",
                    "search_query": q,
                    "use_in": [
                        "logo_card sting after naming the company",
                        "thumbnail corner badge",
                        "lower-third brand chip",
                    ],
                    "do_not": "Do not AI-guess the logo shape/colors",
                    "priority": 1,
                }
            )
        for p in ent.get("people") or []:
            people.append(
                {
                    "id": f"person_{p['name'].lower().replace(' ', '_')}",
                    "name": p["name"],
                    "role": p.get("role", ""),
                    "capture_method": "official_portrait_or_news_still",
                    "search_query": p.get("search") or f"{p['name']} portrait",
                    "use_in": [
                        "person_plate when VO names them",
                        "thumbnail hero face if they drive the story",
                        "proof_quote card with real photo",
                    ],
                    "do_not": (
                        "Do not invent a photoreal face without a real reference image. "
                        "If no photo found, use official title card + org logo, then keep searching."
                    ),
                    "reference_first_ai": (
                        "Optional: image_edit with captured portrait as reference for "
                        "style/grade match — never pure text-to-face invent."
                    ),
                    "priority": 1,
                }
            )

    return {
        "topic": topic,
        "policy": (
            "News about products/services must SHOW company logos and relevant public "
            "figures (real captures), not name-only lower-thirds."
        ),
        "entities": entities,
        "logo_captures": logos,
        "person_captures": people,
        "news_image_hints": [
            {
                "title": h.get("title"),
                "url": h.get("url"),
                "action": "Check article for usable logo/portrait stills (credit outlet)",
            }
            for h in (news_hits or [])[:8]
        ],
        "capcut_identity_recipe": [
            "Import logo PNG with transparency when possible",
            "Person plate: circular or 3D card crop of real photo + name + role",
            "When VO says company name → cut to logo sting ≤1.5s",
            "When VO says CEO/AG/judge name → cut to real portrait ≤2.5s",
            "Thumbnail: largest face or product + 2–5 word text overlay",
        ],
    }


def thumbnail_concepts_with_identity(
    topic: str,
    title: str,
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """High-CTR thumb recipes that expect REAL face/logo assets in CapCut."""
    primary_person = None
    primary_company = None
    for e in entities:
        if e.get("people") and not primary_person:
            primary_person = e["people"][0]
        if e.get("company") and e["company"] != "Unknown" and not primary_company:
            primary_company = e["company"]

    person_name = (primary_person or {}).get("name") or "the leader in this story"
    company = primary_company or "the company"

    return [
        {
            "concept_id": "t1",
            "headline": title[:70],
            "subtext": f"{company} in the spotlight",
            "layout": "face_left_text_right",
            "visual_description": (
                f"COMPOSITE THUMBNAIL (CapCut): place REAL captured photo of {person_name} "
                f"on left third (high-contrast grade, cyan rim light), dark navy background, "
                f"REAL {company} logo small badge top-right. Leave right half empty for huge "
                f"text. Do not AI-invent the face — use captured portrait only."
            ),
            "text_overlay": "THIS CHANGES EVERYTHING",
            "emotion": "shock",
            "required_assets": ["person_primary", "logo_primary"],
        },
        {
            "concept_id": "t2",
            "headline": f"{company} just moved",
            "subtext": topic[:50],
            "layout": "logo_vs_product",
            "visual_description": (
                f"COMPOSITE: giant REAL {company} logo center-left on black, product/UI "
                f"screenshot or cinematic code metaphor right, space for number overlay."
            ),
            "text_overlay": "JUST DROPPED",
            "emotion": "urgency",
            "required_assets": ["logo_primary", "ui_screen"],
        },
        {
            "concept_id": "t3",
            "headline": person_name,
            "subtext": "What they just unleashed",
            "layout": "face_plus_big_number",
            "visual_description": (
                f"COMPOSITE: tight crop REAL photo of {person_name} bottom-left looking "
                f"toward camera, dark vignette, top banner space for 3-word claim, "
                f"{company} logo chip."
            ),
            "text_overlay": "EXPLAINED",
            "emotion": "authority",
            "required_assets": ["person_primary", "logo_primary"],
        },
        {
            "concept_id": "t4",
            "headline": "Why it matters to you",
            "subtext": topic[:40],
            "layout": "product_center_text_banner",
            "visual_description": (
                "COMPOSITE: real product UI screenshot (blur sensitive data) full-bleed "
                "darkened 40%, cyan accent bars, room for banner text."
            ),
            "text_overlay": "WHY IT MATTERS",
            "emotion": "curiosity",
            "required_assets": ["ui_screen"],
        },
        {
            "concept_id": "t5",
            "headline": "The real story",
            "subtext": company,
            "layout": "face_left_text_right",
            "visual_description": (
                f"COMPOSITE dual: REAL {person_name} photo + REAL {company} logo duel frame, "
                "high contrast split, peer-channel CTR energy."
            ),
            "text_overlay": "THE REAL STORY",
            "emotion": "clarity",
            "required_assets": ["person_primary", "logo_primary"],
        },
    ]
