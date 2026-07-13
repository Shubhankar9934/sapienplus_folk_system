"""FOLK web API package.

A thin FastAPI service that serves the exported pipeline artifacts in
``outputs/`` to the Cultural Intelligence Platform frontend. It loads the
JSON deliverables into memory once (see :mod:`folk.api.loader`), derives
cross-country analytics (see :mod:`folk.api.analytics`), and exposes a clean
REST surface (see :mod:`folk.api.app`).
"""

from __future__ import annotations

__all__ = ["create_app"]


def create_app():  # pragma: no cover - thin re-export
    from folk.api.app import create_app as _create_app

    return _create_app()
