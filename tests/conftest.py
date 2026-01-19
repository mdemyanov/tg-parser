"""Pytest configuration and fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Return the fixtures directory path."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def personal_chat_path(fixtures_dir: Path) -> Path:
    """Return path to personal chat fixture."""
    return fixtures_dir / "personal_chat.json"


@pytest.fixture
def supergroup_with_topics_path(fixtures_dir: Path) -> Path:
    """Return path to supergroup with topics fixture."""
    return fixtures_dir / "supergroup_with_topics.json"
