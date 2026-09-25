"""Vercel entrypoint when the project Root Directory is the repo root."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "hub"))

from btasio_hub.main import app  # noqa: E402

__all__ = ["app"]
