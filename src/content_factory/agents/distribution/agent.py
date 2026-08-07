"""Distribution — YouTube upload + social package stubs."""

from __future__ import annotations

from typing import Any

from content_factory.agents.base import AgentContext, mark_done, mark_failed
from content_factory.models.schemas import PublishResult
from content_factory.state import PipelineState
from content_factory.utils.logging import get_logger

log = get_logger(__name__)

PLATFORMS = ["youtube", "x", "instagram", "tiktok", "linkedin", "threads"]


def run_distribution(state: PipelineState) -> dict[str, Any]:
    ctx = AgentContext(state)
    stage = "distribution"
    try:
        seo = state.get("seo_package") or {}
        dry = state.get("dry_run_media", True)
        results: list[PublishResult] = []

        for platform in PLATFORMS:
            if platform == "youtube" and not dry and ctx.settings.youtube_client_secrets:
                results.append(
                    PublishResult(
                        platform="youtube",
                        status="not_implemented",
                        notes="Wire YouTube Data API OAuth upload in Phase 4.",
                    )
                )
            else:
                # Ready-to-post package on disk
                caption = ""
                if platform == "youtube":
                    caption = seo.get("description") or ""
                else:
                    hooks = seo.get("shorts_hooks") or []
                    caption = hooks[0].get("caption", "") if hooks else ""
                path = ctx.store.write_text(
                    f"distribution/{platform}_post.txt",
                    caption or f"Ready-to-post package for {platform}",
                )
                results.append(
                    PublishResult(
                        platform=platform,
                        status="package_written",
                        notes=str(path),
                    )
                )

        payload = [r.model_dump(mode="json") for r in results]
        ctx.store.write_json("distribution/results.json", payload)
        return mark_done(stage, {"publish_results": payload})
    except Exception as exc:  # noqa: BLE001
        log.exception("Distribution failed")
        return mark_failed(stage, str(exc))
