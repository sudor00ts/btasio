"""Vercel default entrypoint. Re-exports the FastAPI app."""

from btasio_hub.main import app

__all__ = ["app"]
