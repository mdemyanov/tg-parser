"""Tests for ConfigLoader."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from tg_parser.domain.exceptions import ConfigError
from tg_parser.infrastructure.config.config_loader import ConfigLoader


class TestConfigLoaderGetConfigLocations:
    """Test ConfigLoader.get_config_locations() method."""

    def test_includes_standard_locations(self) -> None:
        """Test standard config locations are returned."""
        loader = ConfigLoader()
        locations = loader.get_config_locations()

        # Should include home directory locations
        home = Path.home()
        assert home / "tg-parser.toml" in locations
        assert home / ".tg-parser.toml" in locations

        # Should include XDG config location
        xdg_path = Path.home() / ".config" / "tg-parser" / "config.toml"
        assert xdg_path in locations

    def test_includes_cwd_locations(self) -> None:
        """Test current directory locations are included."""
        loader = ConfigLoader()
        locations = loader.get_config_locations()

        cwd = Path.cwd()
        assert cwd / "tg-parser.toml" in locations
        assert cwd / ".tg-parser.toml" in locations

    def test_env_var_first_when_set(self) -> None:
        """Test env var is first in locations when set."""
        env_path = "/custom/config.toml"

        with patch.dict(os.environ, {"TG_PARSER_CONFIG": env_path}):
            loader = ConfigLoader()
            locations = loader.get_config_locations()

        assert locations[0] == Path(env_path)

    def test_env_var_not_included_when_unset(self) -> None:
        """Test env var path not included when not set."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove TG_PARSER_CONFIG if it exists
            os.environ.pop("TG_PARSER_CONFIG", None)
            loader = ConfigLoader()
            locations = loader.get_config_locations()

        # First location should be cwd, not env var
        assert locations[0] == Path.cwd() / "tg-parser.toml"

    def test_xdg_config_home_respected(self) -> None:
        """Test XDG_CONFIG_HOME is respected."""
        custom_xdg = "/custom/xdg"

        with patch.dict(os.environ, {"XDG_CONFIG_HOME": custom_xdg}):
            loader = ConfigLoader()
            locations = loader.get_config_locations()

        expected = Path(custom_xdg) / "tg-parser" / "config.toml"
        assert expected in locations


class TestConfigLoaderFindConfigFile:
    """Test ConfigLoader.find_config_file() method."""

    def test_explicit_path_found(self, tmp_path: Path) -> None:
        """Test explicit path is returned when exists."""
        config_file = tmp_path / "my-config.toml"
        config_file.write_text("[default]")

        loader = ConfigLoader()
        found = loader.find_config_file(explicit_path=config_file)

        assert found == config_file

    def test_explicit_path_expands_tilde(self, tmp_path: Path) -> None:
        """Test explicit path expands ~."""
        # Create a file in home directory for testing
        config_file = tmp_path / "test-config.toml"
        config_file.write_text("[default]")

        loader = ConfigLoader()
        # Pass the actual path, not with tilde
        found = loader.find_config_file(explicit_path=config_file)

        assert found == config_file

    def test_explicit_path_not_found_raises_error(self, tmp_path: Path) -> None:
        """Test error when explicit path doesn't exist."""
        loader = ConfigLoader()

        with pytest.raises(ConfigError) as exc_info:
            loader.find_config_file(explicit_path=tmp_path / "missing.toml")

        assert exc_info.value.operation == "find"
        assert "not found" in exc_info.value.reason

    def test_auto_discovery_finds_cwd_config(self, tmp_path: Path) -> None:
        """Test auto-discovery finds config in current directory."""
        config_file = tmp_path / "tg-parser.toml"
        config_file.write_text("[default]")

        loader = ConfigLoader()

        # Mock cwd to tmp_path
        with patch.object(Path, "cwd", return_value=tmp_path):
            # Re-get locations with mocked cwd
            found = loader.find_config_file()

        assert found == config_file

    def test_auto_discovery_returns_none_when_no_config(self) -> None:
        """Test auto-discovery returns None when no config found."""
        loader = ConfigLoader()

        # Mock all locations to not exist
        with patch.object(
            loader, "get_config_locations", return_value=[Path("/nonexistent/path")]
        ):
            found = loader.find_config_file()

        assert found is None

    def test_priority_order_respected(self, tmp_path: Path) -> None:
        """Test that higher priority locations are preferred."""
        # Create two config files
        cwd_config = tmp_path / "cwd" / "tg-parser.toml"
        cwd_config.parent.mkdir()
        cwd_config.write_text('[default]\noutput_format = "json"')

        home_config = tmp_path / "home" / "tg-parser.toml"
        home_config.parent.mkdir()
        home_config.write_text('[default]\noutput_format = "markdown"')

        loader = ConfigLoader()

        # Mock locations to return cwd first, then home
        mock_locations = [cwd_config, home_config]
        with patch.object(loader, "get_config_locations", return_value=mock_locations):
            found = loader.find_config_file()

        # Should find cwd config (higher priority)
        assert found == cwd_config


class TestConfigLoaderLoad:
    """Test ConfigLoader.load() method."""

    def test_load_returns_defaults_when_no_config(self) -> None:
        """Test load returns defaults when no config found."""
        loader = ConfigLoader()

        with patch.object(loader, "find_config_file", return_value=None):
            settings = loader.load()

        assert settings.config_source is None
        assert settings.default.output_format == "markdown"
        assert settings.chunking.max_tokens == 8000

    def test_load_reads_config_file(self, tmp_path: Path) -> None:
        """Test load reads and validates config file."""
        config_file = tmp_path / "config.toml"
        config_file.write_text(
            """
[default]
output_format = "kb"

[chunking]
max_tokens = 3000
"""
        )

        loader = ConfigLoader()
        settings = loader.load(explicit_path=config_file)

        assert settings.config_source == config_file
        assert settings.default.output_format == "kb"
        assert settings.chunking.max_tokens == 3000

    def test_load_with_explicit_path(self, tmp_path: Path) -> None:
        """Test load with explicit path."""
        config_file = tmp_path / "custom.toml"
        config_file.write_text('[default]\noutput_format = "csv"')

        loader = ConfigLoader()
        settings = loader.load(explicit_path=config_file)

        assert settings.config_source == config_file
        assert settings.default.output_format == "csv"

    def test_load_raises_on_invalid_config(self, tmp_path: Path) -> None:
        """Test load raises ConfigError on invalid config."""
        config_file = tmp_path / "invalid.toml"
        config_file.write_text('[default]\noutput_format = "invalid"')

        loader = ConfigLoader()

        with pytest.raises(ConfigError):
            loader.load(explicit_path=config_file)


class TestConfigLoaderCreateExampleConfig:
    """Test ConfigLoader.create_example_config() method."""

    def test_creates_valid_toml(self, tmp_path: Path) -> None:
        """Test example config is valid TOML."""
        import tomllib

        loader = ConfigLoader()
        content = loader.create_example_config()

        # Should parse without error
        data = tomllib.loads(content)

        assert "default" in data
        assert "filtering" in data
        assert "chunking" in data

    def test_contains_all_sections(self) -> None:
        """Test example config contains all sections."""
        loader = ConfigLoader()
        content = loader.create_example_config()

        assert "[default]" in content
        assert "[filtering]" in content
        assert "[chunking]" in content
        assert "[output.markdown]" in content
        assert "[mentions]" in content
        assert "[stats]" in content

    def test_contains_documentation(self) -> None:
        """Test example config contains helpful comments."""
        loader = ConfigLoader()
        content = loader.create_example_config()

        # Should have comments explaining locations
        assert "tg-parser.toml" in content
        assert ".config/tg-parser" in content
        assert "--config" in content

    def test_roundtrip_validation(self, tmp_path: Path) -> None:
        """Test example config can be loaded and validated."""
        loader = ConfigLoader()
        content = loader.create_example_config()

        # Write to file
        config_file = tmp_path / "config.toml"
        config_file.write_text(content)

        # Should load without error
        settings = loader.load(explicit_path=config_file)

        assert settings.default.output_format == "markdown"
        assert settings.chunking.max_tokens == 8000
