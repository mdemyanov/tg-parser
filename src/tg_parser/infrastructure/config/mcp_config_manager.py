"""MCP configuration manager for Claude Desktop/Code."""

from __future__ import annotations

import json
import platform
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from tg_parser.domain.exceptions import ConfigError


@dataclass(frozen=True, slots=True)
class MCPServerConfig:
    """MCP server configuration entry."""

    command: str
    args: list[str]


@dataclass(frozen=True, slots=True)
class ApplyResult:
    """Result of applying configuration."""

    config_path: Path
    backup_path: Path | None
    created_new: bool
    updated_existing: bool


TargetApp = Literal["desktop", "code"]


class MCPConfigManager:
    """Manages MCP configuration for Claude applications."""

    SERVER_NAME = "tg-parser"

    def __init__(self, target: TargetApp = "desktop") -> None:
        """Initialize config manager.

        Args:
            target: Target application ('desktop' or 'code').
        """
        self._target = target

    def get_config_path(self) -> Path:
        """Get platform-specific config file path.

        Returns:
            Path to Claude config file.

        Raises:
            ConfigError: If platform is not supported.
        """
        system = platform.system()

        if self._target == "desktop":
            if system == "Darwin":  # macOS
                return (
                    Path.home()
                    / "Library/Application Support/Claude/claude_desktop_config.json"
                )
            elif system == "Windows":
                appdata = Path.home() / "AppData/Roaming"
                return appdata / "Claude/claude_desktop_config.json"
            elif system == "Linux":
                return Path.home() / ".config/Claude/claude_desktop_config.json"
        elif self._target == "code":
            # Claude Code config paths
            if system == "Darwin":
                return (
                    Path.home()
                    / "Library/Application Support/Claude/claude_desktop_config.json"
                )
            elif system == "Windows":
                appdata = Path.home() / "AppData/Roaming"
                return appdata / "Claude/claude_desktop_config.json"
            elif system == "Linux":
                return Path.home() / ".config/Claude/claude_desktop_config.json"

        raise ConfigError("get_config_path", f"Unsupported platform: {system}")

    def is_in_venv(self) -> bool:
        """Check if running in a virtual environment.

        Returns:
            True if in venv, False otherwise.
        """
        return sys.prefix != sys.base_prefix

    def get_executable_config(self, use_uv_run: bool = False) -> MCPServerConfig:
        """Determine the executable command for MCP server.

        Uses venv Python path if in venv, otherwise uses uvx or uv run.

        Args:
            use_uv_run: If True, use 'uv run' instead of 'uvx' for system install.

        Returns:
            MCPServerConfig with command and args.
        """
        if self.is_in_venv():
            # Use the full path to Python in the venv
            python_path = sys.executable
            return MCPServerConfig(
                command=python_path, args=["-m", "tg_parser", "mcp"]
            )
        else:
            # Use uv run or uvx for globally installed package
            if use_uv_run:
                return MCPServerConfig(command="uv", args=["run", "tg-parser", "mcp"])
            else:
                return MCPServerConfig(command="uvx", args=["tg-parser", "mcp"])

    def generate_config(self, use_uv_run: bool = False) -> dict[str, object]:
        """Generate MCP configuration for tg-parser.

        Args:
            use_uv_run: If True, use 'uv run' instead of 'uvx' for system install.

        Returns:
            Configuration dict with mcpServers entry.
        """
        server_config = self.get_executable_config(use_uv_run=use_uv_run)
        return {
            "mcpServers": {
                self.SERVER_NAME: {
                    "command": server_config.command,
                    "args": server_config.args,
                }
            }
        }

    def read_existing_config(self, config_path: Path) -> dict[str, object]:
        """Read existing config file.

        Args:
            config_path: Path to config file.

        Returns:
            Existing config or empty dict structure.

        Raises:
            ConfigError: If file contains invalid JSON.
        """
        if not config_path.exists():
            return {"mcpServers": {}}

        try:
            content = config_path.read_text(encoding="utf-8")
            if not content.strip():
                return {"mcpServers": {}}
            data = json.loads(content)
            if not isinstance(data, dict):
                return {"mcpServers": {}}
            if "mcpServers" not in data:
                data["mcpServers"] = {}
            return data
        except json.JSONDecodeError as e:
            raise ConfigError("read", f"Invalid JSON in {config_path}: {e}") from e

    def merge_config(
        self, existing: dict[str, object], new_config: dict[str, object]
    ) -> dict[str, object]:
        """Merge new tg-parser config into existing config.

        Preserves other mcpServers entries.

        Args:
            existing: Existing configuration.
            new_config: New configuration to merge.

        Returns:
            Merged configuration.
        """
        result = dict(existing)

        # Ensure mcpServers exists
        if "mcpServers" not in result:
            result["mcpServers"] = {}

        # Get new server config
        new_servers = new_config.get("mcpServers", {})
        if isinstance(new_servers, dict):
            existing_servers = result.get("mcpServers", {})
            if isinstance(existing_servers, dict):
                existing_servers[self.SERVER_NAME] = new_servers.get(self.SERVER_NAME)
                result["mcpServers"] = existing_servers

        return result

    def create_backup(self, config_path: Path) -> Path | None:
        """Create a backup of existing config file.

        Args:
            config_path: Path to config file.

        Returns:
            Path to backup file, or None if original didn't exist.
        """
        if not config_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.with_suffix(f".{timestamp}.backup")
        shutil.copy2(config_path, backup_path)
        return backup_path

    def apply_config(
        self,
        dry_run: bool = False,
        create_backup: bool = True,
        use_uv_run: bool = False,
    ) -> ApplyResult:
        """Apply MCP configuration to Claude config file.

        Args:
            dry_run: If True, don't actually write the file.
            create_backup: If True, create backup before modifying.
            use_uv_run: If True, use 'uv run' instead of 'uvx' for system install.

        Returns:
            ApplyResult with details of the operation.

        Raises:
            ConfigError: If operation fails.
        """
        config_path = self.get_config_path()
        created_new = not config_path.exists()

        # Read existing config
        existing = self.read_existing_config(config_path)

        # Check if we're updating existing entry
        existing_servers = existing.get("mcpServers", {})
        updated_existing = (
            isinstance(existing_servers, dict) and self.SERVER_NAME in existing_servers
        )

        # Generate and merge config
        new_config = self.generate_config(use_uv_run=use_uv_run)
        merged = self.merge_config(existing, new_config)

        # Create backup if needed
        backup_path: Path | None = None
        if not dry_run and create_backup and not created_new:
            backup_path = self.create_backup(config_path)

        # Write config
        if not dry_run:
            # Ensure parent directory exists
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write with pretty formatting
            config_path.write_text(
                json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        return ApplyResult(
            config_path=config_path,
            backup_path=backup_path,
            created_new=created_new,
            updated_existing=updated_existing,
        )
