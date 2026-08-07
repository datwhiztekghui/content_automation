"""Typer CLI for the content factory."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel

# Ensure project root is on sys.path for `config.settings`
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from config.settings import get_settings, set_active_settings  # noqa: E402
from content_factory.graph import run_pipeline  # noqa: E402
from content_factory.models.schemas import (  # noqa: E402
    PipelineMode,
    StageName,
    resolve_stages,
)
from content_factory.state import initial_state  # noqa: E402
from content_factory.tools.llm import resolve_active_provider  # noqa: E402
from content_factory.utils.artifacts import ArtifactStore, new_run_id  # noqa: E402
from content_factory.utils.logging import setup_logging  # noqa: E402

app = typer.Typer(
    name="content-factory",
    help="Automated multi-agent YouTube content factory (free-local ready).",
    add_completion=False,
)
console = Console()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    mode: str = typer.Option(
        None,
        "--mode",
        "-m",
        help="Pipeline preset: scout | core | media | publish | full | analytics",
    ),
    topic: Optional[str] = typer.Option(
        None, "--topic", "-t", help="Force a topic (skips ranking selection if auto)"
    ),
    stages: Optional[str] = typer.Option(
        None,
        "--stages",
        "-s",
        help="Comma-separated stages (overrides mode), e.g. research,script,factcheck",
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Config profile: free (zero-cost Ollama/DDG/edge-tts) | (default env)",
    ),
    run_id: Optional[str] = typer.Option(
        None, "--run-id", help="Custom run id (default: auto)"
    ),
    headless: bool = typer.Option(
        False, "--headless", help="Non-interactive; file-based approvals"
    ),
    auto_approve: bool = typer.Option(
        False, "--auto-approve", help="Auto-approve topic and script gates"
    ),
    dry_run_media: Optional[bool] = typer.Option(
        None,
        "--dry-run-media/--live-media",
        help="Skip media synthesis (default: dry unless --profile free)",
    ),
    skip_scout: bool = typer.Option(
        False,
        "--skip-scout",
        help="Skip trend scout (use with --topic for research→script)",
    ),
    resume: Optional[str] = typer.Option(
        None, "--resume", help="Resume run id (loads prior artifacts where possible)"
    ),
) -> None:
    """Run the content factory pipeline."""
    if ctx.invoked_subcommand is not None:
        return

    base = get_settings()
    profile_name = profile or base.default_profile or ""
    settings = base.apply_profile(profile_name) if profile_name else base
    set_active_settings(settings)
    setup_logging(settings.log_level)

    mode_str = mode or settings.default_mode
    try:
        pipeline_mode = PipelineMode(mode_str.lower())
    except ValueError:
        console.print(f"[red]Unknown mode:[/red] {mode_str}")
        raise typer.Exit(1)

    try:
        enabled = resolve_stages(
            pipeline_mode,
            stage_csv=stages,
            skip_scout=skip_scout or bool(topic and pipeline_mode == PipelineMode.CORE),
        )
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1)

    if topic and StageName.TREND_SCOUT not in enabled:
        if StageName.AWAIT_TOPIC not in enabled and StageName.DEEP_RESEARCH in enabled:
            enabled = [StageName.AWAIT_TOPIC, *enabled]

    if topic and pipeline_mode == PipelineMode.CORE and not stages:
        enabled = [s for s in enabled if s != StageName.TREND_SCOUT]
        if StageName.AWAIT_TOPIC not in enabled:
            enabled = [StageName.AWAIT_TOPIC, *enabled]

    rid = resume or run_id or new_run_id()
    store = ArtifactStore(settings.runs_dir, rid)

    headless_flag = headless or settings.headless
    auto_flag = auto_approve or settings.auto_approve

    # Media dry-run default: free profile lives TTS; otherwise dry
    if dry_run_media is None:
        dry_flag = False if profile_name == "free" else True
    else:
        dry_flag = dry_run_media

    state = initial_state(
        run_id=rid,
        mode=pipeline_mode,
        enabled_stages=enabled,
        topic_hint=topic or "",
        headless=headless_flag,
        auto_approve=auto_flag,
        dry_run_media=dry_flag,
    )

    if resume:
        for key, rel in [
            ("approved_topic", "approvals/topic.json"),
            ("research_brief", "research/brief.json"),
            ("script_draft", "script/draft.json"),
            ("script_final", "script/final.json"),
            ("topic_candidates", "topics/candidates.json"),
        ]:
            data = store.read_json(rel)
            if data is None:
                continue
            if key == "approved_topic" and isinstance(data, dict) and "approved" in data:
                state["approved_topic"] = data["approved"]
            else:
                state[key] = data  # type: ignore[literal-required]

    llm_prov = resolve_active_provider(settings)
    store.write_json(
        "run_config.json",
        {
            "run_id": rid,
            "mode": pipeline_mode.value,
            "profile": profile_name or None,
            "stages": [s.value for s in enabled],
            "topic": topic,
            "headless": headless_flag,
            "auto_approve": auto_flag,
            "dry_run_media": dry_flag,
            "llm_provider_resolved": llm_prov,
            "search_provider": settings.resolve_search_provider(),
            "tts_provider": settings.resolve_tts_provider(),
        },
    )

    console.print(
        Panel.fit(
            f"[bold]Content Factory[/bold]\n"
            f"Run: {rid}\n"
            f"Profile: {profile_name or 'default'}\n"
            f"LLM: {llm_prov} | Search: {settings.resolve_search_provider()} | "
            f"TTS: {settings.resolve_tts_provider()}\n"
            f"Mode: {pipeline_mode.value}\n"
            f"Stages: {', '.join(s.value for s in enabled)}\n"
            f"Topic: {topic or '(discover)'}\n"
            f"Output: {store.root}",
            title="Starting",
        )
    )

    if profile_name == "free" and llm_prov == "none":
        console.print(
            "[yellow]Tip:[/yellow] No free LLM detected. Heuristic mode will run.\n"
            "  Ollama Cloud (free tier): create a key at https://ollama.com/settings/keys\n"
            "  then set OLLAMA_API_KEY=... in .env and re-run --profile free\n"
            "  Or install local Ollama: https://ollama.com  then  ollama pull qwen2.5:7b"
        )

    try:
        final = run_pipeline(state)
    finally:
        set_active_settings(None)

    store.write_json("final_state.json", dict(final))

    status = final.get("stage_status") or {}
    errors = final.get("errors") or []
    console.print("\n[bold]Stage status[/bold]")
    for k, v in status.items():
        color = {
            "completed": "green",
            "skipped": "yellow",
            "failed": "red",
            "awaiting_approval": "magenta",
        }.get(v, "white")
        console.print(f"  [{color}]{k}: {v}[/{color}]")

    if errors:
        console.print("\n[red]Errors:[/red]")
        for e in errors:
            console.print(f"  - {e}")
        raise typer.Exit(1)

    awaiting = [k for k, v in status.items() if v == "awaiting_approval"]
    if awaiting:
        console.print(
            f"\n[magenta]Paused for approval:[/magenta] {', '.join(awaiting)}\n"
            f"See {store.root / 'approvals'}"
        )
        raise typer.Exit(0)

    console.print(f"\n[green]Done.[/green] Artifacts in [bold]{store.root}[/bold]")
    if final.get("approved_topic"):
        console.print(f"Topic: {final['approved_topic'].get('title')}")
    if final.get("script_final"):
        console.print(
            f"Script words: {final['script_final'].get('word_count')} | "
            f"~{final['script_final'].get('estimated_runtime_minutes')} min"
        )
    voice = final.get("voice_package") or {}
    if voice.get("audio_paths"):
        console.print(f"Audio: {voice['audio_paths'][0]}")


@app.command("list-stages")
def list_stages() -> None:
    """List available pipeline stages and mode presets."""
    console.print("[bold]Stages[/bold]")
    for s in StageName:
        console.print(f"  - {s.value}")
    console.print("\n[bold]Modes[/bold]")
    for m in PipelineMode:
        console.print(f"  - {m.value}")
    console.print("\n[bold]Profiles[/bold]")
    console.print("  - free  (Ollama + DuckDuckGo + edge-tts, $0)")


@app.command("doctor")
def doctor() -> None:
    """Check free-stack readiness (Ollama Cloud, local Ollama, search, TTS)."""
    settings = get_settings()
    from content_factory.tools.llm import (
        ollama_cloud_configured,
        ollama_cloud_reachable,
        ollama_local_reachable,
        resolve_active_provider,
    )

    console.print("[bold]Content Factory doctor[/bold]\n")
    console.print(f"LLM_PROVIDER setting: {settings.llm_provider}")
    console.print(f"Resolved LLM: {resolve_active_provider(settings)}")
    cloud_key = bool(settings.get_ollama_cloud_api_key())
    console.print(f"Ollama Cloud API key set: {cloud_key}")
    console.print(f"Ollama Cloud model: {settings.ollama_cloud_model}")
    if cloud_key:
        console.print(f"Ollama Cloud reachable: {ollama_cloud_reachable(settings)}")
    console.print(f"Local Ollama reachable: {ollama_local_reachable(settings)}")
    console.print(f"Local Ollama model: {settings.ollama_model}")
    console.print(f"Search: {settings.resolve_search_provider()}")
    console.print(f"TTS: {settings.resolve_tts_provider()} ({settings.edge_tts_voice})")
    try:
        import edge_tts  # noqa: F401

        console.print("edge-tts package: installed")
    except ImportError:
        console.print("[yellow]edge-tts package: missing[/yellow] → pip install edge-tts")
    try:
        import duckduckgo_search  # noqa: F401

        console.print("duckduckgo-search: installed")
    except ImportError:
        try:
            import ddgs  # noqa: F401

            console.print("ddgs: installed")
        except ImportError:
            console.print(
                "[yellow]duckduckgo-search: missing[/yellow] → pip install ddgs"
            )
    console.print("\nFree tier tips:")
    console.print("  • Ollama Cloud free bars (session + weekly) are shared — don't burn them on retries")
    console.print("  • Smaller OLLAMA_CLOUD_MODEL stretches free quota")
    console.print("  • Key: https://ollama.com/settings/keys → OLLAMA_API_KEY in .env")
    console.print("\nFree run example:")
    console.print(
        '  python run.py --profile free --mode core --topic "Your topic" --auto-approve'
    )


if __name__ == "__main__":
    app()
