"""Identity assets: real logos + real public-figure photos on Virtual Studio glass panels.

Peer channels show the company and the person. We plan CAPTURE (official/news
sources), not invented deepfakes. Optional reference-first Imagine only after
a real photo is on disk. All identity assets map onto Chloe's floating screens.
"""

from __future__ import annotations

import re
from typing import Any

# Topic keywords → entities the editor MUST put on glass panels
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
        "keys": ["openai", "chatgpt", "gpt-4", "gpt-5", "sora", "astra", "o1", "o3"],
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
        "keys": ["google", "deepmind", "gemini", "alphabet", "wayland", "veo"],
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
        "keys": ["microsoft", "copilot", "azure"],
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
        "keys": ["nvidia", "blackwell", "cuda", "jensen", "nvlink"],
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
        "keys": ["xai", "grok", "elon musk"],
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
        "keys": ["tesla", "optimus", "fsd", "dojo"],
        "company": "Tesla",
        "products": ["Tesla", "Optimus", "FSD"],
        "people": [
            {
                "name": "Elon Musk",
                "role": "CEO, Tesla",
                "search": "Elon Musk Tesla official portrait",
            }
        ],
        "logo_search": ["Tesla logo official"],
    },
    {
        "keys": ["apple", "iphone", "tim cook", "apple intelligence"],
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
        "keys": ["alibaba", "qwen", "tongyi"],
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
        "keys": [
            "bytedance",
            "byte-dance",
            "byte dance",
            "tiktok",
            "douyin",
            "seedance",
            "10 trillion",
            "10t parameter",
        ],
        "company": "ByteDance",
        "products": ["ByteDance", "TikTok", "Douyin"],
        "people": [
            {
                "name": "Liang Rubo",
                "role": "CEO, ByteDance",
                "search": "Liang Rubo ByteDance CEO official photo",
            }
        ],
        "logo_search": [
            "ByteDance logo official",
            "TikTok logo official transparent PNG",
        ],
    },
    {
        "keys": ["deepseek", "deep seek"],
        "company": "DeepSeek",
        "products": ["DeepSeek"],
        "people": [
            {
                "name": "Liang Wenfeng",
                "role": "CEO, DeepSeek",
                "search": "Liang Wenfeng DeepSeek founder portrait",
            }
        ],
        "logo_search": ["DeepSeek logo official"],
    },
    {
        "keys": ["amazon", "aws", "bedrock", "anthropic partnership"],
        "company": "Amazon",
        "products": ["Amazon", "AWS", "Bedrock"],
        "people": [
            {
                "name": "Andy Jassy",
                "role": "CEO, Amazon",
                "search": "Andy Jassy Amazon CEO portrait",
            }
        ],
        "logo_search": ["Amazon logo official", "AWS logo official"],
    },
    {
        "keys": ["figure ai", "figure robotics", "helix"],
        "company": "Figure",
        "products": ["Figure", "Helix"],
        "people": [
            {
                "name": "Brett Adcock",
                "role": "CEO, Figure",
                "search": "Brett Adcock Figure AI CEO portrait",
            }
        ],
        "logo_search": ["Figure AI logo official"],
    },
    {
        "keys": ["new mexico", "torrez", "public nuisance", "biedscheid"],
        "company": "Meta",
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
                for f in found:
                    if f["company"] == key:
                        names = {p["name"] for p in f["people"]}
                        for p in entry["people"]:
                            if p["name"] not in names:
                                f["people"].append(p)
                        # merge logo searches
                        for q in entry.get("logo_search") or []:
                            if q not in f["logo_search"]:
                                f["logo_search"].append(q)
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
    """Editor + pipeline checklist: capture real logos and real faces for studio screens."""
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
                        "floating transparent glass panel behind Chloe",
                        "thumbnail glowing screen",
                        "lower-third brand chip on glass",
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
                        "framed in transparent glass on the floating panel behind Chloe",
                        "thumbnail hero face if they drive the story",
                        "proof_quote card with real photo on glass",
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
            "figures (real captures) mapped onto Chloe's floating studio screens."
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
            "Person plate: place real photo inside a floating transparent glass frame next to Chloe",
            "When VO quotes someone, put published quote + portrait on glass",
            "When VO says company name → logo appears on Chloe's floating panel",
            "Thumbnail: Chloe pointing/gesturing to the largest floating screen with face or product",
            "Tech Frontier badge upper-right on all generative stills",
        ],
    }


def thumbnail_concepts_with_identity(
    topic: str,
    title: str,
    entities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """High-CTR thumb recipes: Virtual Studio + Chloe + real identity assets."""
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
            "layout": "anchor_left_screen_right",
            "visual_description": (
                f"COMPOSITE THUMBNAIL (CapCut): Chloe standing left in her teal virtual studio. "
                f"She holds her transparent tablet, pointing to a massive glowing glass panel on the right. "
                f"Inside the panel: REAL captured photo of {person_name} and REAL {company} logo. "
                f"Giant CapCut text overlays the panel. Tech Frontier badge top-right."
            ),
            "text_overlay": "THIS CHANGES EVERYTHING",
            "emotion": "shock",
            "required_assets": ["person_primary", "logo_primary"],
        },
        {
            "concept_id": "t2",
            "headline": f"{company} just moved",
            "subtext": topic[:50],
            "layout": "anchor_center_split_screens",
            "visual_description": (
                f"COMPOSITE: Chloe standing center, looking up. Behind her, the globe background. "
                f"To her left, a floating panel with the REAL {company} logo. To her right, a panel "
                f"showing a product UI screenshot. Text banner across the top. Tech Frontier badge."
            ),
            "text_overlay": "JUST DROPPED",
            "emotion": "urgency",
            "required_assets": ["logo_primary", "ui_screen"],
        },
        {
            "concept_id": "t3",
            "headline": person_name,
            "subtext": "What they just unleashed",
            "layout": "anchor_face_panel",
            "visual_description": (
                f"COMPOSITE: Chloe medium shot left; giant glass panel right with tight crop "
                f"REAL photo of {person_name}, dark vignette, 3-word claim banner, {company} logo chip."
            ),
            "text_overlay": "EXPLAINED",
            "emotion": "authority",
            "required_assets": ["person_primary", "logo_primary"],
        },
        {
            "concept_id": "t4",
            "headline": "Why it matters to you",
            "subtext": topic[:40],
            "layout": "anchor_hologram_overlay",
            "visual_description": (
                "COMPOSITE: Chloe swiping her transparent tablet. A giant glowing transparent UI panel "
                "fills the right side containing a real product screenshot. Top right Tech Frontier logo."
            ),
            "text_overlay": "WHY IT MATTERS",
            "emotion": "curiosity",
            "required_assets": ["ui_screen"],
        },
        {
            "concept_id": "t5",
            "headline": "The real story",
            "subtext": company,
            "layout": "anchor_dual_identity",
            "visual_description": (
                f"COMPOSITE dual glass: REAL {person_name} photo + REAL {company} logo flanking Chloe, "
                "high contrast split, peer-channel CTR energy, Tech Frontier badge."
            ),
            "text_overlay": "THE REAL STORY",
            "emotion": "clarity",
            "required_assets": ["person_primary", "logo_primary"],
        },
    ]
