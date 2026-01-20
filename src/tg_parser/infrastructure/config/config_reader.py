"""Configuration file reader using tomllib and pydantic."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from tg_parser.domain.exceptions import ConfigError
from tg_parser.domain.value_objects.config_settings import (
    ChunkingSettings,
    ConfigSettings,
    DefaultSettings,
    FilteringSettings,
    MarkdownOutputSettings,
    MentionsSettings,
    StatsSettings,
)


class DefaultSettingsModel(BaseModel):
    """Pydantic model for [default] section."""

    output_format: Literal["markdown", "kb", "json", "csv"] = "markdown"
    output_dir: str | None = None


class FilteringSettingsModel(BaseModel):
    """Pydantic model for [filtering] section."""

    exclude_service: bool = True
    exclude_empty: bool = True
    exclude_forwards: bool = False
    min_message_length: int = Field(default=0, ge=0)


class ChunkingSettingsModel(BaseModel):
    """Pydantic model for [chunking] section."""

    strategy: Literal["fixed", "topic", "hybrid"] = "fixed"
    max_tokens: int = Field(default=8000, gt=0)


class MarkdownOutputModel(BaseModel):
    """Pydantic model for [output.markdown] section."""

    include_extraction_guide: bool = False
    no_frontmatter: bool = False


class MentionsSettingsModel(BaseModel):
    """Pydantic model for [mentions] section."""

    min_count: int = Field(default=1, ge=1)
    output_format: Literal["table", "json"] = "table"


class StatsSettingsModel(BaseModel):
    """Pydantic model for [stats] section."""

    top_senders: int = Field(default=10, ge=1)


class TgParserConfigModel(BaseModel):
    """Root Pydantic model for config validation."""

    default: DefaultSettingsModel = Field(default_factory=DefaultSettingsModel)
    filtering: FilteringSettingsModel = Field(default_factory=FilteringSettingsModel)
    chunking: ChunkingSettingsModel = Field(default_factory=ChunkingSettingsModel)
    output_markdown: MarkdownOutputModel = Field(default_factory=MarkdownOutputModel)
    mentions: MentionsSettingsModel = Field(default_factory=MentionsSettingsModel)
    stats: StatsSettingsModel = Field(default_factory=StatsSettingsModel)


class FileConfigReader:
    """Reads and validates TOML configuration files."""

    def read(self, path: Path) -> dict[str, Any]:
        """Read TOML file and return raw dict.

        Args:
            path: Path to TOML config file.

        Returns:
            Parsed configuration dict.

        Raises:
            ConfigError: If file cannot be read or parsed.
        """
        if not path.exists():
            raise ConfigError("read", f"Config file not found: {path}")

        try:
            content = path.read_text(encoding="utf-8")
            return tomllib.loads(content)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError("parse", f"Invalid TOML in {path}: {e}") from e
        except OSError as e:
            raise ConfigError("read", f"Cannot read {path}: {e}") from e

    def validate(self, data: dict[str, Any]) -> TgParserConfigModel:
        """Validate raw config dict against schema.

        Args:
            data: Raw configuration dict.

        Returns:
            Validated Pydantic model.

        Raises:
            ConfigError: If validation fails.
        """
        try:
            # Handle nested 'output.markdown' key from TOML
            if "output" in data and isinstance(data["output"], dict):
                output_data = data["output"]
                if "markdown" in output_data:
                    data["output_markdown"] = output_data["markdown"]
                del data["output"]

            return TgParserConfigModel.model_validate(data)
        except Exception as e:
            raise ConfigError("validate", f"Invalid configuration: {e}") from e

    def to_settings(
        self,
        model: TgParserConfigModel,
        source: Path | None = None,
    ) -> ConfigSettings:
        """Convert Pydantic model to immutable ConfigSettings.

        Args:
            model: Validated Pydantic model.
            source: Path to config file (for metadata).

        Returns:
            Immutable ConfigSettings dataclass.
        """
        output_dir = (
            Path(model.default.output_dir).expanduser()
            if model.default.output_dir
            else None
        )

        return ConfigSettings(
            default=DefaultSettings(
                output_format=model.default.output_format,
                output_dir=output_dir,
            ),
            filtering=FilteringSettings(
                exclude_service=model.filtering.exclude_service,
                exclude_empty=model.filtering.exclude_empty,
                exclude_forwards=model.filtering.exclude_forwards,
                min_message_length=model.filtering.min_message_length,
            ),
            chunking=ChunkingSettings(
                strategy=model.chunking.strategy,
                max_tokens=model.chunking.max_tokens,
            ),
            output_markdown=MarkdownOutputSettings(
                include_extraction_guide=model.output_markdown.include_extraction_guide,
                no_frontmatter=model.output_markdown.no_frontmatter,
            ),
            mentions=MentionsSettings(
                min_count=model.mentions.min_count,
                output_format=model.mentions.output_format,
            ),
            stats=StatsSettings(
                top_senders=model.stats.top_senders,
            ),
            config_source=source,
        )
