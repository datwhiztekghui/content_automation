"""Re-synthesize voice for a run using natural SSML edge-tts (per section)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from config.settings import Settings, set_active_settings  # noqa: E402
from content_factory.tools.speech_text import narration_for_tts  # noqa: E402
from content_factory.tools.tts import synthesize  # noqa: E402


def main(run_id: str) -> None:
    run = ROOT / "data" / "runs" / run_id
    voice = run / "voice"
    voice.mkdir(parents=True, exist_ok=True)
    script_path = run / "script" / "final.json"
    if not script_path.exists():
        script_path = run / "script" / "draft.json"
    script = json.loads(script_path.read_text(encoding="utf-8"))

    settings = Settings().apply_profile("free")
    set_active_settings(settings)
    try:
        parts: list[str] = []
        paths: list[Path] = []
        for i, sec in enumerate(script.get("sections") or []):
            text = narration_for_tts(sec.get("narration") or "")
            if not text.strip():
                continue
            parts.append(text)
            sid = sec.get("id") or f"s{i}"
            out = voice / f"section_{i:02d}_{sid}.mp3"
            print(f"synth {sid} chars={len(text)}")
            meta = synthesize(
                text,
                out,
                settings=settings,
                provider="edge",
            )
            print(
                f"  bytes={meta.get('bytes')} mode={meta.get('mode')} voice={meta.get('voice')}"
            )
            paths.append(out)

        full = "\n\n".join(parts)
        (voice / "narration_full.txt").write_text(full, encoding="utf-8")

        if not paths:
            print("No audio sections produced")
            return

        # Prefer ffmpeg concat
        out_full = voice / "narration.mp3"
        lst = voice / "concat_list.txt"
        lst.write_text(
            "".join(f"file '{p.name}'\n" for p in paths),
            encoding="utf-8",
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
                str(out_full),
            ],
            cwd=str(voice),
            capture_output=True,
            text=True,
        )
        if r.returncode == 0 and out_full.exists():
            print(f"Wrote {out_full} ({out_full.stat().st_size} bytes)")
        else:
            # Fallback: copy first section if ffmpeg missing
            print("ffmpeg concat failed:", (r.stderr or "")[-300:])
            import shutil

            shutil.copyfile(paths[0], out_full)
            print(f"Fallback copied first section to {out_full}")
            print("Install ffmpeg to stitch full narration.")
    finally:
        set_active_settings(None)


if __name__ == "__main__":
    rid = sys.argv[1] if len(sys.argv) > 1 else "20260807T134022Z_6494630c"
    main(rid)
