"""Read aggregated insights for Trend Scout priors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_recent_insights(learnings_dir: Path, limit: int = 20) -> list[dict[str, Any]]:
    path = Path(learnings_dir) / "insights.jsonl"
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    out: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out
