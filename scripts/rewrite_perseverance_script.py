"""One-off: rewrite Perseverance script (tight FT style) + optional Ava TTS."""

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

RUN = ROOT / "data" / "runs" / "20260810T015240Z_2d72ec67"


def build_script() -> VideoScript:
    sections = [
        ScriptSection(
            id="hook",
            title="Hook",
            start_timestamp="00:00",
            end_timestamp="00:35",
            narration=(
                "About ninety percent of the distance NASA's Perseverance has driven on Mars "
                "was autonomous. Not assisted. Not mostly remote-controlled with a little help. "
                "Autonomous — the rover sensing, deciding, and rolling while Earth was light-minutes away. "
                "Ars Technica just put that number in plain English, and if you care about robots, AI, or "
                "what happens when latency makes live control a joke, this is the story."
            ),
            visual_cues=[
                "Chloe glass panel: 90% AUTONOMOUS",
                "Perseverance traverse still",
            ],
            on_screen_text=["90% of distance · autonomous", "Ars Technica · Aug 2026"],
            source_callouts=["Ars Technica — Eric Berger"],
        ),
        ScriptSection(
            id="why_it_matters",
            title="Why It Matters",
            start_timestamp="00:35",
            end_timestamp="02:00",
            narration=(
                "Here's why the number hits. One-way radio delay between Earth and Mars runs from a few "
                "minutes to more than twenty, depending on where the planets sit. You cannot joystick a "
                "rover through a boulder field in real time. Older missions leaned hard on daily "
                "telecommands — plan a path on Earth, uplink it, hope nothing moved. "
                "Curiosity, still working after more than a decade, has driven tens of kilometers. "
                "Ars notes it at about thirty-eight point six kilometers, with only a small slice of that "
                "done under true self-driving. IEEE Spectrum puts Curiosity's autonomous share around "
                "six point two percent. Perseverance flipped the ratio: roughly ninety percent of its "
                "odometer without a human calling each meter. That is not a press-release adjective. "
                "That is a different operating model for science on another planet."
            ),
            visual_cues=[
                "Earth-Mars delay graphic",
                "Curiosity vs Perseverance comparison card",
            ],
            on_screen_text=[
                "Light-minutes of delay",
                "Curiosity ~6.2% autonomous",
                "Perseverance ~90%",
            ],
            source_callouts=["Ars Technica", "IEEE Spectrum"],
        ),
        ScriptSection(
            id="explanation",
            title="How It Works",
            start_timestamp="02:00",
            end_timestamp="04:30",
            narration=(
                "How does a car-sized robot pull that off on a world of loose rock and soft sand? "
                "Perseverance carries a Vision Compute Element — onboard hardware built for seeing and "
                "deciding while the wheels still turn. IEEE Spectrum describes the software as Enhanced "
                "Autonomous Navigation, or E-Nav. In practice: cameras and other sensors build a live "
                "sense of the terrain; the software picks a safe line; the drive system executes; the "
                "loop keeps running without waiting for Pasadena to approve every meter. "
                "It is not highway speed. Ars cites a maximum wheel speed around one hundred fifty meters "
                "per hour — a careful crawl that buys safety when a bad rock can end a multi-billion-dollar "
                "mission. The point is not thrills. The point is continuous progress when Earth cannot "
                "babysit. Earlier Auto-Nav systems on Mars helped; Perseverance's stack was designed so "
                "sensing and planning happen in motion, not as a stop-and-wait ritual between uplinks."
            ),
            visual_cues=[
                "ENav diagram on glass",
                "Vision Compute Element callout",
                "slow traverse B-roll",
            ],
            on_screen_text=[
                "Vision Compute Element",
                "E-Nav",
                "~150 meters per hour max",
            ],
            source_callouts=[
                "IEEE Spectrum",
                "JPL Mars 2020 mobility",
                "Ars Technica",
            ],
        ),
        ScriptSection(
            id="benchmarks_demos",
            title="Benchmarks & Evidence",
            start_timestamp="04:30",
            end_timestamp="06:30",
            narration=(
                "Numbers, not vibes. Ars reports Perseverance past roughly forty-five kilometers of total "
                "traverse, with about ninety percent of that distance autonomous. IEEE Spectrum, looking "
                "at an earlier checkpoint around sol thirteen twelve — late October twenty twenty-four — "
                "already had the same story: about ninety percent autonomous for Perseverance versus about "
                "six point two percent for Curiosity. NASA Mars has also publicized single-drive records, "
                "including an autonomous push of four hundred eleven meters in one go. "
                "Put those side by side and the pattern is clear. Curiosity still needs humans for most "
                "of the odometer. Perseverance mostly does not. That is the milestone. "
                "Caveat, because adults use caveats: autonomy share can shift with terrain, mission phase, "
                "and how engineers count autonomous versus supervised segments. The public reporting from "
                "Ars and IEEE is consistent enough that mostly self-driven is no longer a rumor."
            ),
            visual_cues=[
                "kinetic 90% vs 6.2%",
                "45+ km odometer",
                "411 m single drive",
            ],
            on_screen_text=[
                "~45+ km driven",
                "90% vs 6.2%",
                "411 m single autonomous drive",
            ],
            source_callouts=["Ars Technica Aug 2026", "IEEE Spectrum", "NASA Mars"],
        ),
        ScriptSection(
            id="implications",
            title="Implications",
            start_timestamp="06:30",
            end_timestamp="08:15",
            narration=(
                "So what changes if a Mars rover mostly drives itself? Science first. Every hour not spent "
                "waiting on a path plan is an hour cameras, spectrometers, and sample hardware can work. "
                "Mission ops second. Teams stop micromanaging wheel tracks and spend more time on targets "
                "that matter — rock units, sample caches, the sample-return puzzle still hanging over the "
                "program. Third, the template for elsewhere. Lunar far-side ops, icy moons, or any place "
                "where delay or bandwidth makes teleoperation painful will steal this playbook. "
                "And yes, there is a terrestrial echo. Self-driving on Mars is not a highway demo. "
                "It is extreme-environment autonomy: sparse compute, ugly terrain, zero tow truck. "
                "If the stack holds, the winners are not just space agencies. They are anyone shipping "
                "robots into places humans cannot sit in the loop."
            ),
            visual_cues=[
                "ops workload split",
                "sample science glass card",
                "extreme-env robot metaphor",
            ],
            on_screen_text=[
                "More science per sol",
                "Less path babysitting",
                "Template for high-latency worlds",
            ],
            source_callouts=["Ars Technica analysis", "Mars 2020 mission context"],
        ),
        ScriptSection(
            id="bigger_picture",
            title="Bigger Picture",
            start_timestamp="08:15",
            end_timestamp="09:45",
            narration=(
                "Zoom out. Spirit and Opportunity taught us rovers could survive years and still need "
                "daily human path craft. Curiosity pushed distance and science while keeping people deep "
                "in the navigation loop. Perseverance was built after those lessons, with autonomy as a "
                "first-class design goal, not a bolt-on demo. "
                "That arc matches what you are seeing in AI writ large: less human in every step, more "
                "human on the goals and machine on the meters. Parameter counts get the headlines on Earth. "
                "On Mars, the quiet flex is odometer share — how much ground a robot can take without "
                "asking permission. The first true self-driving success story on another planet is not a "
                "splashy chat demo. It is a machine that kept rolling when the radio lag made remote "
                "driving a bad joke."
            ),
            visual_cues=[
                "timeline Spirit to Curiosity to Perseverance",
                "odometer share graphic",
            ],
            on_screen_text=[
                "Spirit / Opportunity",
                "Curiosity",
                "Perseverance · ~90% auto",
            ],
            source_callouts=["Mission history", "Ars Technica"],
        ),
        ScriptSection(
            id="cta",
            title="Close & CTA",
            start_timestamp="09:45",
            end_timestamp="10:30",
            narration=(
                "Bottom line: about ninety percent of Perseverance's driven distance has been autonomous, "
                "orders of magnitude more self-directed than Curiosity's share, according to reporting from "
                "Ars Technica and IEEE Spectrum. Slow wheels. Fast decisions relative to Earth. "
                "If you want more breakdowns like this — real numbers, real sources, no fluff — stick "
                "around on AIInfoRoom and tell us which robot story we should tackle next."
            ),
            visual_cues=["end glass panel recap", "soft subscribe plate"],
            on_screen_text=["~90% autonomous", "Sources: Ars · IEEE"],
            source_callouts=["Ars Technica", "IEEE Spectrum"],
        ),
    ]
    return VideoScript(
        title_working="Mars Just Got a Real Self-Driving Success Story",
        topic_title="Perseverance Mars Rover 90% Autonomous Driving Milestone",
        sections=sections,
        soft_cta=sections[-1].narration,
    ).recompute_stats()


def write_script(script: VideoScript) -> None:
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
    (script_dir / "rewrite_notes.json").write_text(
        json.dumps(
            {
                "style": "FT-curiosity + Strunk/White Elements of Style",
                "rules_applied": [
                    "omit needless words",
                    "active voice",
                    "concrete numbers once per claim — no section rehash",
                    "no AI cliches (picture this, game-changer, delve, landscape, unlock, in short)",
                    "no repeated cold-open in every section",
                    "definite specific language over vague hype",
                ],
                "voice_target": "en-US-AvaNeural",
                "word_count": script.word_count,
                "estimated_runtime_minutes": script.estimated_runtime_minutes,
                "prior_word_count": 2316,
                "primary_sources": [
                    "https://arstechnica.com/space/2026/08/the-first-self-driving-vehicle-on-mars-has-proven-to-be-a-smashing-success/",
                    "https://spectrum.ieee.org/perseverance-mars-rover-autonomous-driving",
                ],
                "fact_corrections": [
                    "Prior draft falsely treated 90% as unverified; Ars/IEEE report it as mission fact",
                    "Replaced invented Nav2/RDRS mash with Vision Compute Element + ENav",
                    "Added Curiosity ~6.2% contrast and ~150 m/h max speed from reporting",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def synth_ava(script: VideoScript) -> None:
    settings = get_settings().apply_profile("free")
    voice = "en-US-AvaNeural"
    out_dir = RUN / "voice" / "ava_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    s = settings.model_copy(update={"edge_tts_voice": voice, "tts_provider": "edge"})
    section_paths: list[str] = []
    for i, sec in enumerate(script.sections):
        cleaned = narration_for_tts(sec.narration)
        sec_out = out_dir / f"section_{i:02d}_{sec.id}.mp3"
        meta = synthesize(cleaned, sec_out, settings=s, provider="edge")
        section_paths.append(str(sec_out))
        print(f"Ava {sec.id}: {meta.get('bytes')} bytes ({len(cleaned.split())} words)")
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
    # Convenience copy as primary Ava pick for this rewrite
    primary = RUN / "voice" / "ava"
    primary.mkdir(parents=True, exist_ok=True)
    if full_mp3.exists():
        (primary / "narration_v2_tight.mp3").write_bytes(full_mp3.read_bytes())
    (out_dir / "voice_meta.json").write_text(
        json.dumps(
            {
                "voice": voice,
                "version": "v2_tight_ft_style",
                "sections": section_paths,
                "full": str(full_mp3),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> None:
    script = build_script()
    write_script(script)
    print(
        f"Script written: {script.word_count} words · ~{script.estimated_runtime_minutes} min"
    )
    for sec in script.sections:
        print(f"  {sec.id}: {len(sec.narration.split())} words")
    if "--no-tts" in sys.argv:
        return
    print("Synthesizing en-US-AvaNeural…")
    synth_ava(script)
    print("Done.")


if __name__ == "__main__":
    main()
