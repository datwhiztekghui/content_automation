"""Per-run artifact storage (JSON + Markdown)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from content_factory.utils.logging import get_logger

log = get_logger(__name__)


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{uuid.uuid4().hex[:8]}"


class ArtifactStore:
    """Write and read run artifacts under data/runs/<run_id>/."""

    def __init__(self, runs_dir: Path, run_id: str) -> None:
        self.run_id = run_id
        self.root = Path(runs_dir) / run_id
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, *parts: str) -> Path:
        p = self.root.joinpath(*parts)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def write_json(self, relative: str, data: Any) -> Path:
        path = self.path(relative)
        if isinstance(data, BaseModel):
            payload = data.model_dump(mode="json")
        else:
            payload = data
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )
        log.debug("Wrote %s", path)
        return path

    def write_text(self, relative: str, content: str) -> Path:
        path = self.path(relative)
        path.write_text(content, encoding="utf-8")
        log.debug("Wrote %s", path)
        return path

    def read_json(self, relative: str) -> Any:
        path = self.path(relative)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def read_text(self, relative: str) -> str | None:
        path = self.path(relative)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def exists(self, relative: str) -> bool:
        return self.path(relative).exists()

    def write_model_pair(
        self,
        basename: str,
        model: BaseModel,
        markdown: str | None = None,
    ) -> tuple[Path, Path | None]:
        """Write both JSON and optional Markdown for a structured artifact."""
        json_path = self.write_json(f"{basename}.json", model)
        md_path = None
        if markdown is not None:
            md_path = self.write_text(f"{basename}.md", markdown)
        return json_path, md_path
