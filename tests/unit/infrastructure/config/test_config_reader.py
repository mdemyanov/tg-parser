"""Tests for FileConfigReader."""

from __future__ import annotations

from pathlib import Path

import pytest

from tg_parser.domain.exceptions import ConfigError
from tg_parser.infrastructure.config.config_reader import (
    FileConfigReader,
    TgParserConfigModel,
)


class TestFileConfigReaderRead:
    """Test FileConfigReader.read() method."""

    def test_read_valid_toml(self, tmp_path: Path) -> None:
        """Test reading valid TOML file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[default]
output_format = "json"
output_dir = "~/exports"

[chunking]
max_tokens = 4000
"""
        )

        reader = FileConfigReader()
        data = reader.read(config_file)

        assert data["default"]["output_format"] == "json"
        assert data["default"]["output_dir"] == "~/exports"
        assert data["chunking"]["max_tokens"] == 4000

    def test_read_minimal_toml(self, tmp_path: Path) -> None:
        """Test reading minimal TOML file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("[default]")

        reader = FileConfigReader()
        data = reader.read(config_file)

        assert "default" in data
        assert data["default"] == {}

    def test_read_nonexistent_file(self, tmp_path: Path) -> None:
        """Test reading non-existent file raises ConfigError."""
        reader = FileConfigReader()

        with pytest.raises(ConfigError) as exc_info:
            reader.read(tmp_path / "nonexistent.toml")

        assert exc_info.value.operation == "read"
        assert "not found" in exc_info.value.reason

    def test_read_invalid_toml(self, tmp_path: Path) -> None:
        """Test reading invalid TOML raises ConfigError."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("invalid toml {{{")

        reader = FileConfigReader()

        with pytest.raises(ConfigError) as exc_info:
            reader.read(config_file)

        assert exc_info.value.operation == "parse"
        assert "Invalid TOML" in exc_info.value.reason


class TestFileConfigReaderValidate:
    """Test FileConfigReader.validate() method."""

    def test_validate_valid_data(self) -> None:
        """Test validation of valid config data."""
        reader = FileConfigReader()
        data = {
            "default": {"output_format": "kb"},
            "chunking": {"max_tokens": 5000},
        }

        model = reader.validate(data)

        assert model.default.output_format == "kb"
        assert model.chunking.max_tokens == 5000
        # Defaults for non-specified
        assert model.filtering.exclude_service is True

    def test_validate_empty_data(self) -> None:
        """Test validation of empty config."""
        reader = FileConfigReader()
        data: dict[str, object] = {}

        model = reader.validate(data)

        # All defaults
        assert model.default.output_format == "markdown"
        assert model.chunking.max_tokens == 8000

    def test_validate_nested_output_markdown(self) -> None:
        """Test validation handles [output.markdown] section."""
        reader = FileConfigReader()
        data = {
            "output": {
                "markdown": {
                    "include_extraction_guide": True,
                    "no_frontmatter": True,
                }
            }
        }

        model = reader.validate(data)

        assert model.output_markdown.include_extraction_guide is True
        assert model.output_markdown.no_frontmatter is True

    def test_validate_invalid_format(self) -> None:
        """Test validation rejects invalid output_format."""
        reader = FileConfigReader()
        data = {"default": {"output_format": "invalid_format"}}

        with pytest.raises(ConfigError) as exc_info:
            reader.validate(data)

        assert exc_info.value.operation == "validate"
        assert "Invalid configuration" in exc_info.value.reason

    def test_validate_invalid_max_tokens_zero(self) -> None:
        """Test validation rejects zero max_tokens."""
        reader = FileConfigReader()
        data = {"chunking": {"max_tokens": 0}}

        with pytest.raises(ConfigError) as exc_info:
            reader.validate(data)

        assert exc_info.value.operation == "validate"

    def test_validate_invalid_max_tokens_negative(self) -> None:
        """Test validation rejects negative max_tokens."""
        reader = FileConfigReader()
        data = {"chunking": {"max_tokens": -100}}

        with pytest.raises(ConfigError) as exc_info:
            reader.validate(data)

        assert exc_info.value.operation == "validate"

    def test_validate_invalid_min_count_zero(self) -> None:
        """Test validation rejects zero min_count."""
        reader = FileConfigReader()
        data = {"mentions": {"min_count": 0}}

        with pytest.raises(ConfigError) as exc_info:
            reader.validate(data)

        assert exc_info.value.operation == "validate"

    def test_validate_invalid_strategy(self) -> None:
        """Test validation rejects invalid strategy."""
        reader = FileConfigReader()
        data = {"chunking": {"strategy": "invalid_strategy"}}

        with pytest.raises(ConfigError) as exc_info:
            reader.validate(data)

        assert exc_info.value.operation == "validate"

    def test_validate_all_formats(self) -> None:
        """Test validation accepts all valid formats."""
        reader = FileConfigReader()

        for fmt in ("markdown", "kb", "json", "csv"):
            data = {"default": {"output_format": fmt}}
            model = reader.validate(data)
            assert model.default.output_format == fmt

    def test_validate_all_strategies(self) -> None:
        """Test validation accepts all valid strategies."""
        reader = FileConfigReader()

        for strategy in ("fixed", "topic", "hybrid"):
            data = {"chunking": {"strategy": strategy}}
            model = reader.validate(data)
            assert model.chunking.strategy == strategy


class TestFileConfigReaderToSettings:
    """Test FileConfigReader.to_settings() method."""

    def test_to_settings_basic_conversion(self) -> None:
        """Test basic conversion to ConfigSettings."""
        reader = FileConfigReader()
        model = TgParserConfigModel()

        settings = reader.to_settings(model, source=None)

        assert settings.default.output_format == "markdown"
        assert settings.config_source is None

    def test_to_settings_with_source(self) -> None:
        """Test conversion preserves source path."""
        reader = FileConfigReader()
        model = TgParserConfigModel()
        source = Path("/test/config.toml")

        settings = reader.to_settings(model, source=source)

        assert settings.config_source == source

    def test_to_settings_path_expansion(self) -> None:
        """Test conversion expands ~ in output_dir."""
        reader = FileConfigReader()
        data = {"default": {"output_dir": "~/exports"}}
        model = reader.validate(data)

        settings = reader.to_settings(model, source=None)

        assert settings.default.output_dir is not None
        assert str(settings.default.output_dir).startswith(str(Path.home()))
        assert "exports" in str(settings.default.output_dir)

    def test_to_settings_all_values(self) -> None:
        """Test conversion preserves all values."""
        reader = FileConfigReader()
        data = {
            "default": {"output_format": "json", "output_dir": "/tmp/out"},
            "filtering": {
                "exclude_service": False,
                "exclude_empty": False,
                "exclude_forwards": True,
                "min_message_length": 10,
            },
            "chunking": {"strategy": "hybrid", "max_tokens": 4000},
            "output_markdown": {
                "include_extraction_guide": True,
                "no_frontmatter": True,
            },
            "mentions": {"min_count": 5, "output_format": "json"},
            "stats": {"top_senders": 20},
        }
        model = reader.validate(data)

        settings = reader.to_settings(model, source=Path("/cfg"))

        assert settings.default.output_format == "json"
        assert settings.default.output_dir == Path("/tmp/out")
        assert settings.filtering.exclude_service is False
        assert settings.filtering.exclude_empty is False
        assert settings.filtering.exclude_forwards is True
        assert settings.filtering.min_message_length == 10
        assert settings.chunking.strategy == "hybrid"
        assert settings.chunking.max_tokens == 4000
        assert settings.output_markdown.include_extraction_guide is True
        assert settings.output_markdown.no_frontmatter is True
        assert settings.mentions.min_count == 5
        assert settings.mentions.output_format == "json"
        assert settings.stats.top_senders == 20
        assert settings.config_source == Path("/cfg")
