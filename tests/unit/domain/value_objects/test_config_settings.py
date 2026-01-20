"""Tests for ConfigSettings value object."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from tg_parser.domain.value_objects.config_settings import (
    ChunkingSettings,
    ConfigSettings,
    DefaultSettings,
    FilteringSettings,
    MarkdownOutputSettings,
    MentionsSettings,
    StatsSettings,
)


class TestDefaultSettings:
    """Test DefaultSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = DefaultSettings()

        assert settings.output_format == "markdown"
        assert settings.output_dir is None

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = DefaultSettings(
            output_format="json",
            output_dir=Path("/tmp/output"),
        )

        assert settings.output_format == "json"
        assert settings.output_dir == Path("/tmp/output")

    def test_immutability(self) -> None:
        """Test that settings are frozen."""
        settings = DefaultSettings()

        with pytest.raises(FrozenInstanceError):
            settings.output_format = "json"  # type: ignore[misc]


class TestFilteringSettings:
    """Test FilteringSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = FilteringSettings()

        assert settings.exclude_service is True
        assert settings.exclude_empty is True
        assert settings.exclude_forwards is False
        assert settings.min_message_length == 0

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = FilteringSettings(
            exclude_service=False,
            exclude_empty=False,
            exclude_forwards=True,
            min_message_length=10,
        )

        assert settings.exclude_service is False
        assert settings.exclude_empty is False
        assert settings.exclude_forwards is True
        assert settings.min_message_length == 10


class TestChunkingSettings:
    """Test ChunkingSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = ChunkingSettings()

        assert settings.strategy == "fixed"
        assert settings.max_tokens == 8000

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = ChunkingSettings(strategy="hybrid", max_tokens=4000)

        assert settings.strategy == "hybrid"
        assert settings.max_tokens == 4000


class TestMarkdownOutputSettings:
    """Test MarkdownOutputSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = MarkdownOutputSettings()

        assert settings.include_extraction_guide is False
        assert settings.no_frontmatter is False

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = MarkdownOutputSettings(
            include_extraction_guide=True,
            no_frontmatter=True,
        )

        assert settings.include_extraction_guide is True
        assert settings.no_frontmatter is True


class TestMentionsSettings:
    """Test MentionsSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = MentionsSettings()

        assert settings.min_count == 1
        assert settings.output_format == "table"

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = MentionsSettings(min_count=5, output_format="json")

        assert settings.min_count == 5
        assert settings.output_format == "json"


class TestStatsSettings:
    """Test StatsSettings dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        settings = StatsSettings()

        assert settings.top_senders == 10

    def test_custom_values(self) -> None:
        """Test custom values."""
        settings = StatsSettings(top_senders=20)

        assert settings.top_senders == 20


class TestConfigSettings:
    """Test ConfigSettings composite dataclass."""

    def test_default_values(self) -> None:
        """Test all default values."""
        settings = ConfigSettings()

        # Check defaults
        assert settings.default.output_format == "markdown"
        assert settings.default.output_dir is None
        assert settings.filtering.exclude_service is True
        assert settings.chunking.max_tokens == 8000
        assert settings.output_markdown.include_extraction_guide is False
        assert settings.mentions.min_count == 1
        assert settings.stats.top_senders == 10
        assert settings.config_source is None

    def test_immutability(self) -> None:
        """Test that ConfigSettings is frozen."""
        settings = ConfigSettings()

        with pytest.raises(FrozenInstanceError):
            settings.config_source = Path("/some/path")  # type: ignore[misc]

    def test_custom_values(self) -> None:
        """Test creating settings with custom values."""
        settings = ConfigSettings(
            default=DefaultSettings(output_format="json"),
            chunking=ChunkingSettings(max_tokens=4000),
            config_source=Path("/test/config.toml"),
        )

        assert settings.default.output_format == "json"
        assert settings.chunking.max_tokens == 4000
        assert settings.config_source == Path("/test/config.toml")
        # Non-specified should have defaults
        assert settings.filtering.exclude_service is True

    def test_partial_override(self) -> None:
        """Test partial override of nested settings."""
        settings = ConfigSettings(
            default=DefaultSettings(output_format="kb"),
        )

        # Overridden
        assert settings.default.output_format == "kb"
        # Not overridden - uses default
        assert settings.default.output_dir is None
        assert settings.filtering.exclude_service is True
