"""Configuration settings value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass(frozen=True, slots=True)
class DefaultSettings:
    """Default output settings."""

    output_format: Literal["markdown", "kb", "json", "csv"] = "markdown"
    output_dir: Path | None = None


@dataclass(frozen=True, slots=True)
class FilteringSettings:
    """Default filtering settings."""

    exclude_service: bool = True
    exclude_empty: bool = True
    exclude_forwards: bool = False
    min_message_length: int = 0


@dataclass(frozen=True, slots=True)
class ChunkingSettings:
    """Default chunking settings."""

    strategy: Literal["fixed", "topic", "hybrid"] = "fixed"
    max_tokens: int = 8000


@dataclass(frozen=True, slots=True)
class MarkdownOutputSettings:
    """Markdown output specific settings."""

    include_extraction_guide: bool = False
    no_frontmatter: bool = False


@dataclass(frozen=True, slots=True)
class MentionsSettings:
    """Mentions command defaults."""

    min_count: int = 1
    output_format: Literal["table", "json"] = "table"


@dataclass(frozen=True, slots=True)
class StatsSettings:
    """Stats command defaults."""

    top_senders: int = 10


@dataclass(frozen=True, slots=True)
class ConfigSettings:
    """Complete configuration settings - immutable.

    This is the main configuration object that aggregates all settings
    from the TOML config file. It is immutable (frozen dataclass) to
    ensure configuration cannot be accidentally modified at runtime.
    """

    default: DefaultSettings = field(default_factory=DefaultSettings)
    filtering: FilteringSettings = field(default_factory=FilteringSettings)
    chunking: ChunkingSettings = field(default_factory=ChunkingSettings)
    output_markdown: MarkdownOutputSettings = field(
        default_factory=MarkdownOutputSettings
    )
    mentions: MentionsSettings = field(default_factory=MentionsSettings)
    stats: StatsSettings = field(default_factory=StatsSettings)

    # Metadata - where this config came from
    config_source: Path | None = None
