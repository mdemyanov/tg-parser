"""Configuration loader with file discovery and merge logic."""

from __future__ import annotations

import os
from pathlib import Path

from tg_parser.domain.exceptions import ConfigError
from tg_parser.domain.value_objects.config_settings import ConfigSettings
from tg_parser.infrastructure.config.config_reader import (
    FileConfigReader,
    TgParserConfigModel,
)


class ConfigLoader:
    """Loads configuration from files with priority-based discovery.

    Config file priority (highest to lowest):
    1. --config CLI flag (explicit_path)
    2. TG_PARSER_CONFIG environment variable
    3. ./tg-parser.toml (current directory)
    4. ./.tg-parser.toml (current directory, hidden)
    5. ~/tg-parser.toml (home directory)
    6. ~/.tg-parser.toml (home directory, hidden)
    7. ~/.config/tg-parser/config.toml (XDG config)
    8. Built-in defaults
    """

    CONFIG_FILE_NAMES = (
        "tg-parser.toml",
        ".tg-parser.toml",
    )

    ENV_VAR_NAME = "TG_PARSER_CONFIG"

    def __init__(self) -> None:
        """Initialize config loader."""
        self._reader = FileConfigReader()

    def get_config_locations(self) -> list[Path]:
        """Get all standard config file locations (in priority order).

        Returns:
            List of paths where config files are searched (highest priority first).
        """
        locations: list[Path] = []

        # 1. Environment variable (highest priority)
        env_path = os.environ.get(self.ENV_VAR_NAME)
        if env_path:
            locations.append(Path(env_path).expanduser())

        # 2. Current directory
        cwd = Path.cwd()
        for name in self.CONFIG_FILE_NAMES:
            locations.append(cwd / name)

        # 3. Home directory
        home = Path.home()
        for name in self.CONFIG_FILE_NAMES:
            locations.append(home / name)

        # 4. XDG config directory (~/.config/tg-parser/)
        xdg_config = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config"))
        locations.append(xdg_config / "tg-parser" / "config.toml")

        return locations

    def find_config_file(self, explicit_path: Path | None = None) -> Path | None:
        """Find the first existing config file.

        Args:
            explicit_path: Explicitly specified config path (--config flag).

        Returns:
            Path to config file if found, None otherwise.

        Raises:
            ConfigError: If explicit path doesn't exist.
        """
        # Explicit path has highest priority
        if explicit_path is not None:
            expanded = explicit_path.expanduser()
            if not expanded.exists():
                raise ConfigError(
                    "find", f"Specified config file not found: {expanded}"
                )
            return expanded

        # Search standard locations
        for location in self.get_config_locations():
            if location.exists() and location.is_file():
                return location

        return None

    def load(self, explicit_path: Path | None = None) -> ConfigSettings:
        """Load configuration with full discovery and validation.

        Args:
            explicit_path: Path from --config CLI flag.

        Returns:
            ConfigSettings with merged configuration.
        """
        config_path = self.find_config_file(explicit_path)

        if config_path is None:
            # No config file found - return defaults
            return self._reader.to_settings(TgParserConfigModel(), source=None)

        # Read and validate config file
        raw_data = self._reader.read(config_path)
        validated = self._reader.validate(raw_data)

        return self._reader.to_settings(validated, source=config_path)

    def create_example_config(self) -> str:
        """Generate example TOML configuration content.

        Returns:
            Example config file content as string.
        """
        return """# tg-parser configuration file
# Place this file at:
#   ./tg-parser.toml (project-specific)
#   ~/.tg-parser.toml (user-wide)
#   ~/.config/tg-parser/config.toml (XDG standard)
# Or specify with: tg-parser --config /path/to/config.toml

[default]
# Output format: markdown, kb, json, csv
output_format = "markdown"
# Default output directory (supports ~ for home)
# output_dir = "~/Documents/tg-exports"

[filtering]
# Exclude service messages (join/leave/pin)
exclude_service = true
# Exclude messages with empty text
exclude_empty = true
# Exclude forwarded messages
exclude_forwards = false
# Minimum message length to include
min_message_length = 0

[chunking]
# Chunking strategy: fixed, topic, hybrid
strategy = "fixed"
# Maximum tokens per chunk
max_tokens = 8000

[output.markdown]
# Include Russian extraction guide template
include_extraction_guide = false
# Exclude YAML frontmatter (kb format only)
no_frontmatter = false

[mentions]
# Minimum mention count to show
min_count = 1
# Output format: table, json
output_format = "table"

[stats]
# Number of top senders to show
top_senders = 10
"""
