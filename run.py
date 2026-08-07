#!/usr/bin/env python3
"""Thin entrypoint: python run.py --mode core --topic \"...\" """

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
for p in (ROOT, SRC):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from content_factory.cli import app  # noqa: E402

if __name__ == "__main__":
    app()
