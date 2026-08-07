"""Free TTS backends: edge-tts (default), optional Piper, ElevenLabs later."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from config.settings import Settings, get_settings
from content_factory.tools.speech_text import narration_for_tts, to_ssml
from content_factory.utils.logging import get_logger

log = get_logger(__name__)


class TTSError(RuntimeError):
    pass


def synthesize(
    text: str,
    out_path: Path,
    *,
    settings: Settings | None = None,
    provider: str | None = None,
    use_ssml: bool = True,
) -> dict[str, Any]:
    """Synthesize speech to out_path. Returns metadata dict."""
    settings = settings or get_settings()
    provider = (provider or settings.resolve_tts_provider()).lower()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if provider in {"none", "dry"}:
        raise TTSError("TTS provider is none")

    if provider == "edge":
        return _edge_tts(text, out_path, settings, use_ssml=use_ssml)
    if provider == "piper":
        return _piper(text, out_path, settings)
    if provider == "elevenlabs":
        raise TTSError("ElevenLabs live path not enabled in free stack — use edge")

    return _edge_tts(text, out_path, settings, use_ssml=use_ssml)


def _edge_tts(
    text: str,
    out_path: Path,
    settings: Settings,
    *,
    use_ssml: bool = True,
) -> dict[str, Any]:
    try:
        import edge_tts
    except ImportError as exc:
        raise TTSError("edge-tts not installed. Run: pip install edge-tts") from exc

    voice = settings.edge_tts_voice or "en-GB-RyanNeural"
    # Slightly slower = clearer word separation for tech explainers
    rate = settings.edge_tts_rate or "-8%"
    pitch = getattr(settings, "edge_tts_pitch", None) or "+0Hz"

    if out_path.suffix.lower() not in {".mp3", ".wav"}:
        out_path = out_path.with_suffix(".mp3")

    plain = narration_for_tts(text)
    payload = plain
    mode = "plain"
    if use_ssml:
        # Infer language from voice prefix
        lang = "en-GB" if voice.startswith("en-GB") else "en-US"
        if voice.startswith("en-AU"):
            lang = "en-AU"
        payload = to_ssml(plain, voice=voice, rate=rate, pitch=pitch, lang=lang)
        mode = "ssml"

    async def _run() -> None:
        # When using SSML, rate/pitch are inside SSML; pass neutral kwargs
        if mode == "ssml":
            communicate = edge_tts.Communicate(payload, voice)
        else:
            communicate = edge_tts.Communicate(
                payload, voice, rate=rate, pitch=pitch
            )
        await communicate.save(str(out_path))

    log.info(
        "edge-tts voice=%s rate=%s mode=%s chars=%s → %s",
        voice,
        rate,
        mode,
        len(plain),
        out_path,
    )
    try:
        asyncio.run(_run())
    except Exception as first_exc:  # noqa: BLE001
        # SSML can fail on some voices — fall back to cleaned plain text
        if mode == "ssml":
            log.warning("SSML TTS failed (%s); retrying plain text", first_exc)

            async def _run_plain() -> None:
                communicate = edge_tts.Communicate(
                    plain, voice, rate=rate, pitch=pitch
                )
                await communicate.save(str(out_path))

            try:
                asyncio.run(_run_plain())
                mode = "plain-fallback"
            except RuntimeError:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_run_plain())
                    mode = "plain-fallback"
                finally:
                    loop.close()
        else:
            try:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_run())
                finally:
                    loop.close()
            except Exception as exc:  # noqa: BLE001
                raise TTSError(str(exc)) from exc

    if not out_path.exists() or out_path.stat().st_size == 0:
        raise TTSError("edge-tts produced empty file")

    return {
        "provider": "edge",
        "voice": voice,
        "rate": rate,
        "pitch": pitch,
        "mode": mode,
        "path": str(out_path),
        "format": out_path.suffix.lstrip("."),
        "bytes": out_path.stat().st_size,
        "normalized_chars": len(plain),
    }


def _piper(text: str, out_path: Path, settings: Settings) -> dict[str, Any]:
    model = settings.piper_model_path
    if not model:
        raise TTSError("PIPER_MODEL_PATH not set")
    wav_path = out_path.with_suffix(".wav")
    plain = narration_for_tts(text)
    proc = subprocess.run(
        ["piper", "--model", model, "--output_file", str(wav_path)],
        input=plain.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0 or not wav_path.exists():
        raise TTSError(
            f"Piper failed: {proc.stderr.decode('utf-8', errors='ignore')[:300]}"
        )
    return {
        "provider": "piper",
        "voice": model,
        "path": str(wav_path),
        "format": "wav",
        "bytes": wav_path.stat().st_size,
    }
