"""Shared pytest fixtures."""

from __future__ import annotations

import os

import pytest

# Force the offline deterministic provider for the whole test suite.
os.environ.setdefault("FOLK_PROVIDER_MODE", "mock")


@pytest.fixture(scope="session")
def settings():
    from folk.config import get_settings

    return get_settings()
