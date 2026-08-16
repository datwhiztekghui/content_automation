"""Build ByteDance 10T hybrid-spine script + Ava VO (AIInfoRoom storytelling)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from config.settings import get_settings  # noqa: E402
from content_factory.agents.scriptwriter.agent import script_to_markdown  # noqa: E402
from content_factory.models.schemas import ScriptSection, VideoScript  # noqa: E402
from content_factory.tools.speech_text import narration_for_tts  # noqa: E402
from content_factory.tools.tts import synthesize  # noqa: E402

RUN = ROOT / "data" / "runs" / "bytedance_10t_hybrid"


def build_script() -> VideoScript:
    """Hybrid spine: AI-Rev cold open → Arun stakes → MKBHD point → proof → race → open loop."""
    sections = [
        ScriptSection(
            id="hook",
            title="Hook",
            start_timestamp="00:00",
            end_timestamp="00:18",
            narration=(
                "ByteDance is training a monster AI model with up to ten trillion parameters. "
                "Yes — ten trillion. The TikTok parent just put a Financial Times-sized target on "
                "the frontier race, and the timeline is still buzzing."
            ),
            visual_cues=[
                "Chloe glass panel: 10 TRILLION PARAMETERS",
                "ByteDance + TikTok logo chips",
            ],
            on_screen_text=["10 TRILLION PARAMETERS", "Financial Times report"],
            source_callouts=["Financial Times", "Reuters"],
        ),
        ScriptSection(
            id="why_it_matters",
            title="Why It Matters",
            start_timestamp="00:18",
            end_timestamp="01:30",
            narration=(
                "Here's why it hits. This isn't a lab paper nobody will ship. ByteDance already runs "
                "Doubao — one of China's most-used AI assistants, with hundreds of millions of monthly "
                "users — plus real multimodal muscle in video and three-D. They're spending on data "
                "centers and custom chips. When a company that already owns distribution aims at "
                "Anthropic-scale training, the question isn't 'cool demo?' It's who gets the next "
                "default assistant in markets of billions of people."
            ),
            visual_cues=[
                "Doubao user-scale kinetic card",
                "Data center + chip glass panels",
            ],
            on_screen_text=["Doubao · hundreds of millions MAU", "Distribution + scale"],
            source_callouts=["Financial Times", "The Decoder"],
        ),
        ScriptSection(
            id="explanation",
            title="How It Works",
            start_timestamp="01:30",
            end_timestamp="03:00",
            narration=(
                "Point of this video: is the ten-trillion number a real training bet, or marketing fog? "
                "ByteDance's Seed team — roughly two thousand people — is in early pre-training on a "
                "model that could hit as many as ten trillion parameters. Parameters are the knobs the "
                "model tunes while learning patterns. More knobs can mean more capacity — but architecture, "
                "data quality, and training tricks matter as much or more. Pre-training alone often takes "
                "three to six months; then fine-tuning. Final size isn't locked. Sources say founder "
                "Zhang Yiming told Seed to chase world-leading capabilities long-term, and that ByteDance "
                "has avoided distillation — training on other companies' model outputs — for over a year, "
                "insisting on independent development."
            ),
            visual_cues=[
                "Seed team size card",
                "Pre-train → fine-tune timeline",
                "Zhang Yiming plate if licensed photo available",
            ],
            on_screen_text=[
                "Seed team · ~2,000 people",
                "Early pre-training",
                "Independent development · no distillation",
            ],
            source_callouts=["Financial Times", "Reuters"],
        ),
        ScriptSection(
            id="benchmarks_demos",
            title="Benchmarks & Evidence",
            start_timestamp="03:00",
            end_timestamp="04:40",
            narration=(
                "Context ladder. Ten trillion is more than three times Moonshot AI's Kimi K-three — "
                "about two point eight trillion parameters, currently China's biggest widely cited release "
                "at that class. Industry estimates put Anthropic's Mythos five around eight trillion and "
                "Fable five around five trillion — Anthropic does not officially disclose sizes, so treat "
                "those as estimates, not press-kit facts. The primary public report is the Financial Times, "
                "picked up by Reuters, The Decoder, and The Next Web. What we do not have yet: public "
                "benchmarks, open weights, or a ship date with a product name. Ambition is reported. "
                "Results are not."
            ),
            visual_cues=[
                "Comparison: 10T vs 2.8T vs ~8T / ~5T",
                "Source chips: FT · Reuters · Decoder · TNW",
            ],
            on_screen_text=[
                "10T vs Kimi K3 ~2.8T",
                "Mythos 5 ~8T · Fable 5 ~5T (est.)",
                "No public benchmarks yet",
            ],
            source_callouts=[
                "Financial Times",
                "Reuters",
                "The Decoder",
                "The Next Web",
            ],
        ),
        ScriptSection(
            id="implications",
            title="Implications",
            start_timestamp="04:40",
            end_timestamp="06:00",
            narration=(
                "If training works, multi-trillion models stop being a Western-only club story. "
                "Enterprises watching China will care about access, export controls, and whether "
                "Doubao-class products absorb the gains first. Creators and developers should care "
                "because the real fight isn't the headline number — it's cost per useful answer, "
                "latency to users, and whether independent training beats distillation shortcuts. "
                "Mixture-of-experts systems often activate only a fraction of parameters per token, "
                "so a ten-trillion label can hide a smaller active brain. Efficiency and data still rule "
                "the scoreboard."
            ),
            visual_cues=[
                "MoE active-vs-total diagram",
                "Geo / access implication cards",
            ],
            on_screen_text=[
                "Active params ≠ total params",
                "Access · cost · latency",
            ],
            source_callouts=["Industry context", "Financial Times"],
        ),
        ScriptSection(
            id="bigger_picture",
            title="Bigger Picture",
            start_timestamp="06:00",
            end_timestamp="07:10",
            narration=(
                "Zoom out. China's labs closed gaps fast; Kimi K-three already turned heads. "
                "ByteDance is swinging at Mythos-scale ambition with product distribution behind it. "
                "xAI has been linked to Grok training in the six-to-ten-trillion range, so the ten-T "
                "club is getting crowded. Trillion-parameter models are yesterday's news. Multi-trillion "
                "is the battlefield now. Reporting suggests something could surface around early "
                "twenty twenty-seven if training stays on track — that's a calendar marker, not a promise."
            ),
            visual_cues=[
                "Race map: ByteDance · Moonshot · Anthropic · xAI",
                "2027 window card",
            ],
            on_screen_text=[
                "Multi-trillion battlefield",
                "Early 2027? (if training holds)",
            ],
            source_callouts=["Financial Times", "Reuters"],
        ),
        ScriptSection(
            id="cta",
            title="Close & CTA",
            start_timestamp="07:10",
            end_timestamp="07:50",
            narration=(
                "Bottom line: ByteDance Seed is pre-training toward as many as ten trillion parameters, "
                "per Financial Times reporting — a real scale bet with distribution attached, not a random "
                "blog rumor. Will scale win, or do architecture and data still decide the crown? "
                "Drop your take. If you want more breakdowns like this on AIInfoRoom — numbers, "
                "sources, no fluff — stick around and tell us what race we cover next."
            ),
            visual_cues=["Recap glass panel", "Soft subscribe / comment prompt"],
            on_screen_text=["10T scale bet · FT-reported", "Scale vs architecture?"],
            source_callouts=["Financial Times", "Reuters"],
        ),
    ]
    return VideoScript(
        title_working="ByteDance's 10 Trillion Parameter Bet",
        topic_title="ByteDance training up to 10 trillion parameter AI model",
        sections=sections,
        soft_cta=sections[-1].narration,
    ).recompute_stats()


def write_artifacts(script: VideoScript) -> None:
    RUN.mkdir(parents=True, exist_ok=True)
    script_dir = RUN / "script"
    script_dir.mkdir(parents=True, exist_ok=True)
    payload = script.model_dump(mode="json")
    (script_dir / "final.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (script_dir / "draft.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    md = script_to_markdown(script)
    (script_dir / "final.md").write_text(md, encoding="utf-8")
    (script_dir / "draft.md").write_text(md, encoding="utf-8")
    (script_dir / "narration.txt").write_text(script.full_narration, encoding="utf-8")
    (script_dir / "storytelling.json").write_text(
        json.dumps(
            {
                "spine": "hybrid_mkbhd_arun_airevolution",
                "word_count": script.word_count,
                "estimated_runtime_minutes": script.estimated_runtime_minutes,
                "sources": [
                    "https://www.ft.com/content/9b8383b1-a28d-4940-8c4e-2f0cd21556ef",
                    "https://www.reuters.com/technology/bytedance-targets-mega-ai-model-nearing-anthropics-mythos-ft-reports-2026-08-07/",
                    "https://the-decoder.com/chinas-largest-ai-model-is-being-developed-at-bytedance/",
                    "https://thenextweb.com/news/bytedance-10-trillion-parameter-model-mythos",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def synth_ava(script: VideoScript) -> Path:
    settings = get_settings().apply_profile("free")
    voice = "en-US-AvaNeural"
    out_dir = RUN / "voice" / "ava"
    out_dir.mkdir(parents=True, exist_ok=True)
    s = settings.model_copy(update={"edge_tts_voice": voice, "tts_provider": "edge"})
    section_paths: list[str] = []
    for i, sec in enumerate(script.sections):
        cleaned = narration_for_tts(sec.narration)
        sec_out = out_dir / f"section_{i:02d}_{sec.id}.mp3"
        meta = synthesize(cleaned, sec_out, settings=s, provider="edge")
        section_paths.append(str(sec_out))
        print(f"Ava {sec.id}: {meta.get('bytes')} bytes · {len(cleaned.split())} words")
    full_text = "\n\n".join(narration_for_tts(x.narration) for x in script.sections)
    (out_dir / "narration_full.txt").write_text(full_text, encoding="utf-8")
    full_mp3 = out_dir / "narration.mp3"
    lst = out_dir / "concat_list.txt"
    lst.write_text(
        "".join(f"file '{Path(p).name}'\n" for p in section_paths), encoding="utf-8"
    )
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(full_mp3),
        ],
        cwd=str(out_dir),
        capture_output=True,
        text=True,
    )
    print("concat", r.returncode, full_mp3.stat().st_size if full_mp3.exists() else 0)
    (out_dir / "voice_meta.json").write_text(
        json.dumps(
            {
                "voice": voice,
                "sections": section_paths,
                "full": str(full_mp3),
                "storytelling": "hybrid",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return full_mp3


def main() -> None:
    script = build_script()
    write_artifacts(script)
    print(
        f"Script: {script.word_count} words · ~{script.estimated_runtime_minutes} min"
    )
    for sec in script.sections:
        print(f"  {sec.id}: {len(sec.narration.split())} words")
    if "--no-tts" not in sys.argv:
        print("Synthesizing en-US-AvaNeural…")
        path = synth_ava(script)
        print(f"VO ready: {path}")
    print("Done.")


if __name__ == "__main__":
    main()
