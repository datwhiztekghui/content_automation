"""Build Gemini-ready prompts in Virtual News Studio style (Chloe + glass panels).

Legacy Muse Code packs still work; scenes are framed into Chloe's floating
glass panels with Clarion Frame branding (see peer_style.build_gemini_prompt).

Usage:
  python scripts/build_gemini_prompts.py [run_id]

Writes:
  data/runs/<id>/visuals/GEMINI_PROMPTS.md
  data/runs/<id>/visuals/GEMINI_PROMPTS.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from content_factory.agents.visual_director.identity_assets import (  # noqa: E402
    extract_entities,
)
from content_factory.agents.visual_director.peer_style import (  # noqa: E402
    build_gemini_prompt,
    style_lock,
)


def _company_from_topic(topic: str) -> tuple[str, str]:
    ents = extract_entities(topic, topic)
    if ents:
        c = ents[0]["company"]
        return c, ""
    return "META", ""


def muse_code_shots(company: str) -> list[dict[str, str]]:
    """Full ~8 min pack for Meta Muse Code (peer CGI + logo + burned titles)."""
    c = company or "META"
    shots: list[tuple[str, str, str, str, str]] = [
        # id, scene, main_title, sub_title, extra
        (
            "hook_01",
            "Sleek white-black humanoid robot in a dense blue server hall, holding a holographic tablet labeled META MUSE, cyan eye sensors, three-quarter hero pose",
            "META MUSE",
            "AI CODE AGENT",
            "Holographic META logo sign hanging above like a neon brand billboard.",
        ),
        (
            "hook_02",
            "Humanoid robot pointing at a floating monorepo hologram of millions of glowing file nodes, deep server racks behind",
            "MILLION-FILE",
            "CODEBASES",
            logo_extra(c),
        ),
        (
            "hook_03",
            "Epic ultra-wide GPU cluster cathedral with robot silhouette and volumetric cyan beams",
            "META AI",
            "JUST DROPPED",
            logo_extra(c),
        ),
        (
            "hook_04",
            "Robot dual-wielding two holograms: search results and generated code panels, sparks of light between them",
            "SEARCH + SUMMARIZE",
            "GENERATE",
            logo_extra(c),
        ),
        (
            "why_01",
            "Humanoid robot walking a corridor of endless server cages pulling a glowing thread of code",
            "WHY IT MATTERS",
            "DEVELOPER TIME",
            logo_extra(c),
        ),
        (
            "why_02",
            "Close hero shot of robot face reflecting LED racks, holographic brain-network above its hand",
            "ONBOARDING",
            "HOURS → MINUTES",
            logo_extra(c),
        ),
        (
            "why_03",
            "Robot standing before a multi-monitor coding fortress, hologram IDE floating, dark glass floor reflections",
            "MEET MUSE",
            "BUILT FOR SCALE",
            logo_extra(c),
        ),
        (
            "why_04",
            "Split energy composition: robot left, dual skyline Silicon Valley vs neon Asia right, AI race mood",
            "BIG TECH",
            "CODING WAR",
            logo_extra(c),
        ),
        (
            "why_05",
            "Robot inspecting a holographic tablet showing vector-search / retrieval diagram (abstract, stylish)",
            "LLAMA CODE",
            "+ RETRIEVAL",
            logo_extra(c),
        ),
        (
            "why_06",
            "Cinematic top angle of robot hands over a holographic keyboard of light",
            "AI PAIR",
            "PROGRAMMER",
            logo_extra(c),
        ),
        (
            "why_07",
            "Robot in front of glass tech campus at night with META-style brand hologram in sky (sharp logo)",
            "META AI LAB",
            "NEW WEAPON",
            logo_extra(c),
        ),
        (
            "why_08",
            "Liquid-metal neural lattice forming beside the robot under studio cyan lights",
            "SMART RETRIEVAL",
            "RIGHT SNIPPETS",
            logo_extra(c),
        ),
        (
            "exp_01",
            "Robot explaining a 3D holographic pipeline: Index → Retrieve → Generate, glowing arrows",
            "HOW IT WORKS",
            "3-STEP AGENT",
            logo_extra(c),
        ),
        (
            "exp_02",
            "Robot inside a tunnel of recursive mirrors made of code-light, infinity of files",
            "MASSIVE REPOS",
            "NO PROBLEM",
            logo_extra(c),
        ),
        (
            "exp_03",
            "Robot commanding a conveyor of light-cubes (CI/build metaphor) through a dark factory of servers",
            "INDEXING",
            "AT SCALE",
            logo_extra(c),
        ),
        (
            "exp_04",
            "Extreme close-up robot finger touching a holographic function block that expands into documentation",
            "SUMMARIZE",
            "WHOLE MODULES",
            logo_extra(c),
        ),
        (
            "exp_05",
            "Robot dual holograms: left search bar energy, right code completion streaming as light",
            "WRITE CODE",
            "ACROSS FILES",
            logo_extra(c),
        ),
        (
            "exp_06",
            "Wide ops center wall of soft abstract maps with robot silhouette, mission-control energy",
            "CONTEXT",
            "THAT STICKS",
            logo_extra(c),
        ),
        (
            "exp_07",
            "Robot holding a translucent crystal of layered code strata (architecture layers)",
            "ARCHITECTURE",
            "AWARE AGENT",
            logo_extra(c),
        ),
        (
            "exp_08",
            "Humanoid AI walking between server cages with META logo neon plaque on the cage door",
            "META MUSE",
            "IN THE LOOP",
            logo_extra(c),
        ),
        (
            "exp_09",
            "Robot presenting side-by-side holograms labeled as abstract A/B performance bars (no tiny junk text)",
            "FASTER",
            "CODE NAV",
            logo_extra(c),
        ),
        (
            "exp_10",
            "Dramatic low angle robot under hanging holographic META logo sign like the ByteDance billboard style",
            "THIS IS MUSE",
            "CODE AGENT",
            logo_extra(c),
        ),
        (
            "bench_01",
            "Robot with leaderboard-style holographic columns of light rising (rankings energy)",
            "BENCHMARKS",
            "WHAT WE KNOW",
            logo_extra(c),
        ),
        (
            "bench_02",
            "Robot racing light-trails of commits, speed lines, server hall depth",
            "SPEED",
            "THAT SHIPS",
            logo_extra(c),
        ),
        (
            "bench_03",
            "Split diopter CGI: robot keyboard hands left, GPU cluster right",
            "VS OLD TOOLS",
            "NIGHT & DAY",
            logo_extra(c),
        ),
        (
            "bench_04",
            "Robot stacking translucent holographic layers like dependency strata",
            "DEEP CONTEXT",
            "REAL REPOS",
            logo_extra(c),
        ),
        (
            "bench_05",
            "Classic hacker cyan phosphor glow on robot chrome face, stylish not cheesy",
            "DEMO ENERGY",
            "WATCH CLOSE",
            logo_extra(c),
        ),
        (
            "bench_06",
            "Particles assembling into a skyscraper of light cubes beside the robot (scale metaphor)",
            "SCALE",
            "OF CODEBASES",
            logo_extra(c),
        ),
        (
            "impl_01",
            "Robot in glass boardroom reflection of city night, strategy stakes",
            "FOR TEAMS",
            "ENTERPRISE",
            logo_extra(c),
        ),
        (
            "impl_02",
            "Robot helping a silhouetted developer at a desk (human unrecognizable), partnership mood",
            "JUNIORS",
            "LEVEL UP",
            logo_extra(c),
        ),
        (
            "impl_03",
            "Robot at a glowing vault-like server door, permissions and security mood",
            "RISKS",
            "ACCESS & SAFETY",
            logo_extra(c),
        ),
        (
            "impl_04",
            "City transit night, software-eats-world energy, robot hologram billboard with META mark",
            "INDUSTRY",
            "IMPACT",
            logo_extra(c),
        ),
        (
            "impl_05",
            "Cyan and amber light beams clashing over dark city as robot watches (disruption)",
            "WHO LOSES?",
            "OLD WORKFLOWS",
            logo_extra(c),
        ),
        (
            "impl_06",
            "Global delivery metaphor: robot above fiber light-routes across a dark continent map hologram",
            "OPEN SOURCE?",
            "OR CLOSED",
            logo_extra(c),
        ),
        (
            "big_01",
            "Timeline of glowing nodes (editor history of coding tools) with robot guide figure",
            "BIGGER PICTURE",
            "AGENTS ARRIVE",
            logo_extra(c),
        ),
        (
            "big_02",
            "Server cathedral aisles like a futuristic temple, robot small for scale",
            "THE SHIFT",
            "IS HERE",
            logo_extra(c),
        ),
        (
            "big_03",
            "Sunrise through glass towers with robot on rooftop overlooking the city",
            "WHAT'S NEXT",
            "FOR CODERS",
            logo_extra(c),
        ),
        (
            "big_04",
            "DNA-helix of light code strands coiling around the robot torso, evolution vibe",
            "SOFTWARE",
            "EVOLUTION",
            logo_extra(c),
        ),
        (
            "cta_01",
            "Clean end-card CGI: robot looking at camera, META logo hologram, subscribe space lower third area still has main title",
            "SUBSCRIBE",
            "Clarion Frame",
            logo_extra(c),
        ),
        (
            "cta_02",
            "Soft close: robot powering down holographic Muse panel, city window bokeh",
            "META MUSE",
            "EXPLAINED",
            logo_extra(c),
        ),
        # Thumbnails — text ON image like reference
        (
            "thumb_01",
            "Thumbnail punch: humanoid robot left holding Muse hologram, dense server hall, META logo sign top",
            "META MUSE",
            "CODE AGENT",
            "Maximum CTR, face of robot toward text, huge type right side.",
        ),
        (
            "thumb_02",
            "Thumbnail: extreme close robot eye reflecting code, META badge, dark navy",
            "JUST DROPPED",
            "AI FOR REPOS",
            logo_extra(c),
        ),
        (
            "thumb_03",
            "Thumbnail split: monorepo hologram chaos vs clean generated function light, robot center",
            "MILLION FILES",
            "ONE AGENT",
            logo_extra(c),
        ),
        (
            "thumb_04",
            "Thumbnail low-angle robot under giant META neon logo sign, stormy tech drama",
            "WHY IT MATTERS",
            "FOR YOU",
            logo_extra(c),
        ),
        (
            "thumb_05",
            "Thumbnail robot presenting big holographic title slab, amber-white 3D text dominant",
            "EXPLAINED",
            "IN 8 MINUTES",
            logo_extra(c),
        ),
        (
            "extra_01",
            "Robot army silhouettes faint in depth (one hero sharp), implying agent fleets",
            "AGENT ERA",
            "STARTS NOW",
            logo_extra(c),
        ),
        (
            "extra_02",
            "Holographic META logo explosion of light particles around the robot hero",
            "OFFICIAL",
            "META AI",
            logo_extra(c),
        ),
        (
            "extra_03",
            "Robot handshake with a human silhouette made of light (partnership, not a real celebrity face)",
            "HUMAN + AI",
            "SHIP FASTER",
            logo_extra(c),
        ),
    ]

    out = []
    for sid, scene, main, sub, extra in shots:
        prompt = build_gemini_prompt(
            scene=scene,
            company=c,
            main_title=main,
            sub_title=sub,
            extra=extra,
        )
        out.append(
            {
                "id": sid,
                "section": sid.split("_")[0],
                "main_title": main,
                "sub_title": sub,
                "company_logo": c,
                "prompt": prompt,
            }
        )
    return out


def logo_extra(company: str) -> str:
    return (
        f"Sharp accurate {company} logo on a glowing holographic hanging sign "
        f"(like a neon brand billboard), official colors, crystal clear."
    )


def main(run_id: str) -> None:
    run = ROOT / "data" / "runs" / run_id
    vis = run / "visuals"
    vis.mkdir(parents=True, exist_ok=True)

    topic = "Meta Muse Code AI agent for massive codebases"
    script_path = run / "script" / "final.json"
    if script_path.exists():
        data = json.loads(script_path.read_text(encoding="utf-8"))
        topic = data.get("topic_title") or data.get("title_working") or topic

    company, _ = _company_from_topic(topic)
    if "meta" in topic.lower() or "muse" in topic.lower():
        company = "META"

    items = muse_code_shots(company)
    (vis / "GEMINI_PROMPTS.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    md = [
        "# Gemini image prompts — ByteDance-reference style",
        "",
        f"**Run:** `{run_id}`  ",
        f"**Topic:** {topic}  ",
        f"**Company brand on every hero frame:** {company}",
        "",
        "## Style lock (read once)",
        "",
        f"> {style_lock()}",
        "",
        "## Rules",
        "",
        "1. **DO** put the company **logo** on the image where the story is about that company.",
        "2. **DO** burn **bold English titles** (2–6 words) for the shot’s main claim — like the reference’s “10 TRILLION PARAMETERS”.",
        "3. **DO NOT** include AI generator watermarks (Gemini/Grok/Midjourney stamps).",
        "4. Prefer **humanoid robot hero + server hall + holograms + neon brand sign** for energy.",
        "5. For real human CEOs: composite **real captured photo** in CapCut if Gemini won’t do likenesses; logo+robot still carries the brand.",
        "",
        f"**Total prompts:** {len(items)} (covers ~8 minutes with ~8–12s average hold + Ken Burns / whip cuts)",
        "",
        "---",
        "",
    ]
    for i, it in enumerate(items, 1):
        md.append(f"## {i}. `{it['id']}` — {it['main_title']} / {it['sub_title']}")
        md.append("")
        md.append("```")
        md.append(it["prompt"])
        md.append("```")
        md.append("")

    (vis / "GEMINI_PROMPTS.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {len(items)} prompts → {vis / 'GEMINI_PROMPTS.md'}")


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "20260808T020744Z_d751c42f"
    main(rid)
