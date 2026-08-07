"""Voice Director — natural edge-tts (RyanNeural) with plain-text synthesis.

edge-tts builds its own SSML; we only ever send cleaned plain narration.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import VideoScript, VoicePackage
from content_factory.state import PipelineState
from content_factory.tools.speech_text import narration_for_tts
from content_factory.tools.tts import TTSError, synthesize
from content_factory.utils.logging import get_logger

log = get_logger(__name__)


def _concat_audio(section_paths: list[str], out: Path) -> None:
    """Stitch section MP3s with ffmpeg (copy) or fall back to first section."""
    out = Path(out)
    if not section_paths:
        raise TTSError("No section audio to concat")
    if len(section_paths) == 1:
        shutil.copyfile(section_paths[0], out)
        return
    lst = out.parent / "concat_list.txt"
    lst.write_text(
        "".join(f"file '{Path(p).name}'\n" for p in section_paths),
        encoding="utf-8",
    )
    try:
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
                str(out),
            ],
            cwd=str(out.parent),
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode == 0 and out.exists() and out.stat().st_size > 0:
            return
        log.warning("ffmpeg concat failed: %s", (r.stderr or "")[-200:])
    except FileNotFoundError:
        log.warning("ffmpeg not found; copying first section only")
    shutil.copyfile(section_paths[0], out)


def run_voice_director(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "voice_director"
    try:
        raw = state.get("script_final") or state.get("script_draft")
        if not raw:
            return mark_failed(stage, "No script available for voice")
        script = VideoScript.model_validate(raw)

        section_texts: list[str] = []
        markers = []
        for sec in script.sections:
            cleaned = narration_for_tts(sec.narration)
            section_texts.append(cleaned)
            markers.append(
                {
                    "section_id": sec.id,
                    "title": sec.title,
                    "start_timestamp": sec.start_timestamp,
                    "end_timestamp": sec.end_timestamp,
                    "approx_chars": len(cleaned),
                }
            )

        full_text = "\n\n".join(t for t in section_texts if t)
        narration_path = ctx.store.write_text("voice/narration_full.txt", full_text)

        voice = ctx.settings.edge_tts_voice or "en-GB-RyanNeural"
        rate = ctx.settings.edge_tts_rate or "-8%"
        pitch = ctx.settings.edge_tts_pitch or "+0Hz"

        tts_provider = ctx.settings.resolve_tts_provider()
        force_dry = bool(state.get("dry_run_media", True)) and tts_provider == "elevenlabs"
        want_audio = (
            not force_dry
            and tts_provider not in {"none", "elevenlabs"}
            and bool(full_text.strip())
        )
        if state.get("dry_run_media") is False:
            want_audio = tts_provider not in {"none"} and tts_provider != "elevenlabs"
        if ctx.settings.active_profile == "free" and tts_provider == "edge":
            want_audio = True

        audio_paths: list[str] = []
        voice_settings: dict[str, Any] = {
            "provider": tts_provider,
            "voice": voice,
            "rate": rate,
            "pitch": pitch,
            "mode": "plain",
        }
        dry = True
        meta: dict[str, Any] = {}

        if want_audio:
            out = ctx.store.path("voice/narration.mp3")
            try:
                if len(full_text) > 12000:
                    log.warning(
                        "Narration very long (%s chars); synthesis may take a while",
                        len(full_text),
                    )
                section_paths: list[str] = []
                for i, (sec, cleaned) in enumerate(
                    zip(script.sections, section_texts)
                ):
                    if not cleaned.strip():
                        continue
                    sec_out = ctx.store.path(f"voice/section_{i:02d}_{sec.id}.mp3")
                    sec_meta = synthesize(
                        cleaned,
                        sec_out,
                        settings=ctx.settings,
                        provider=tts_provider if tts_provider != "auto" else "edge",
                    )
                    section_paths.append(sec_meta["path"])
                    log.info(
                        "Section VO %s → %s bytes mode=%s",
                        sec.id,
                        sec_meta.get("bytes"),
                        sec_meta.get("mode"),
                    )

                if section_paths:
                    _concat_audio(section_paths, out)
                    audio_paths = [str(out)]
                    dry = False
                    meta = {
                        "provider": "edge",
                        "voice": voice,
                        "rate": rate,
                        "pitch": pitch,
                        "mode": "sectioned-plain",
                        "path": str(out),
                        "sections": section_paths,
                    }
                    voice_settings.update(meta)
                    log.info("Full narration stitched → %s", out)
            except TTSError as exc:
                log.warning("TTS failed (%s); dry-run text only", exc)
                dry = True
        else:
            log.info(
                "Voice dry-run (provider=%s dry_run_media=%s)",
                tts_provider,
                state.get("dry_run_media"),
            )

        package = VoicePackage(
            voice_id=str(voice_settings.get("voice") or voice),
            voice_settings=voice_settings,
            audio_paths=audio_paths,
            timing_markers=markers,
            dry_run=dry,
            narration_text_path=str(narration_path),
        )

        ctx.store.write_json("voice/package.json", package)
        ctx.store.write_json("voice/timing_markers.json", markers)
        return mark_done(stage, {"voice_package": package.model_dump(mode="json")})
    except Exception as exc:  # noqa: BLE001
        log.exception("Voice Director failed")
        return mark_failed(stage, str(exc))
