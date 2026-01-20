"""Tests for MCP config manager."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest

from tg_parser.domain.exceptions import ConfigError
from tg_parser.infrastructure.config.mcp_config_manager import MCPConfigManager


class TestMCPConfigManager:
    """Test MCPConfigManager."""

    def test_is_in_venv_true_when_prefix_differs(self) -> None:
        """Test venv detection when in venv."""
        manager = MCPConfigManager()
        with patch.object(sys, "prefix", "/venv"):
            with patch.object(sys, "base_prefix", "/usr"):
                assert manager.is_in_venv() is True

    def test_is_in_venv_false_when_prefix_same(self) -> None:
        """Test venv detection when not in venv."""
        manager = MCPConfigManager()
        with patch.object(sys, "prefix", "/usr"):
            with patch.object(sys, "base_prefix", "/usr"):
                assert manager.is_in_venv() is False

    def test_get_executable_config_venv(self) -> None:
        """Test executable config in venv."""
        manager = MCPConfigManager()
        with patch.object(manager, "is_in_venv", return_value=True):
            with patch.object(sys, "executable", "/venv/bin/python"):
                config = manager.get_executable_config()
                assert config.command == "/venv/bin/python"
                assert config.args == ["-m", "tg_parser", "mcp"]

    def test_get_executable_config_system_uvx(self) -> None:
        """Test executable config for system install with uvx."""
        manager = MCPConfigManager()
        with patch.object(manager, "is_in_venv", return_value=False):
            config = manager.get_executable_config(use_uv_run=False)
            assert config.command == "uvx"
            assert config.args == ["tg-parser", "mcp"]

    def test_get_executable_config_system_uv_run(self) -> None:
        """Test executable config for system install with uv run."""
        manager = MCPConfigManager()
        with patch.object(manager, "is_in_venv", return_value=False):
            config = manager.get_executable_config(use_uv_run=True)
            assert config.command == "uv"
            assert config.args == ["run", "tg-parser", "mcp"]

    def test_generate_config_uvx(self) -> None:
        """Test config generation with uvx."""
        manager = MCPConfigManager()
        with patch.object(manager, "is_in_venv", return_value=False):
            config = manager.generate_config(use_uv_run=False)
            assert "mcpServers" in config
            mcp_servers = cast(dict[str, Any], config["mcpServers"])
            assert "tg-parser" in mcp_servers
            server_config = mcp_servers["tg-parser"]
            assert server_config["command"] == "uvx"
            assert server_config["args"] == ["tg-parser", "mcp"]

    def test_generate_config_uv_run(self) -> None:
        """Test config generation with uv run."""
        manager = MCPConfigManager()
        with patch.object(manager, "is_in_venv", return_value=False):
            config = manager.generate_config(use_uv_run=True)
            assert "mcpServers" in config
            mcp_servers = cast(dict[str, Any], config["mcpServers"])
            server_config = mcp_servers["tg-parser"]
            assert server_config["command"] == "uv"
            assert server_config["args"] == ["run", "tg-parser", "mcp"]

    def test_get_config_path_macos_desktop(self) -> None:
        """Test macOS config path for desktop."""
        manager = MCPConfigManager(target="desktop")
        with patch("platform.system", return_value="Darwin"):
            path = manager.get_config_path()
            assert "Library/Application Support/Claude" in str(path)
            assert path.name == "claude_desktop_config.json"

    def test_get_config_path_linux_desktop(self) -> None:
        """Test Linux config path for desktop."""
        manager = MCPConfigManager(target="desktop")
        with patch("platform.system", return_value="Linux"):
            path = manager.get_config_path()
            assert ".config/Claude" in str(path)

    def test_get_config_path_windows_desktop(self) -> None:
        """Test Windows config path for desktop."""
        manager = MCPConfigManager(target="desktop")
        with patch("platform.system", return_value="Windows"):
            path = manager.get_config_path()
            assert "AppData" in str(path) or "Claude" in str(path)

    def test_get_config_path_unsupported_platform(self) -> None:
        """Test unsupported platform raises error."""
        manager = MCPConfigManager(target="desktop")
        with patch("platform.system", return_value="FreeBSD"):
            with pytest.raises(ConfigError) as exc_info:
                manager.get_config_path()
            assert "Unsupported platform" in str(exc_info.value)

    def test_read_existing_config_file_not_exists(self, tmp_path: Path) -> None:
        """Test reading non-existent config."""
        manager = MCPConfigManager()
        result = manager.read_existing_config(tmp_path / "nonexistent.json")
        assert result == {"mcpServers": {}}

    def test_read_existing_config_empty_file(self, tmp_path: Path) -> None:
        """Test reading empty config file."""
        config_path = tmp_path / "config.json"
        config_path.write_text("")
        manager = MCPConfigManager()
        result = manager.read_existing_config(config_path)
        assert result == {"mcpServers": {}}

    def test_read_existing_config_valid_json(self, tmp_path: Path) -> None:
        """Test reading valid config file."""
        config_path = tmp_path / "config.json"
        existing = {"mcpServers": {"other-tool": {"command": "other"}}}
        config_path.write_text(json.dumps(existing))
        manager = MCPConfigManager()
        result = manager.read_existing_config(config_path)
        assert result == existing

    def test_read_existing_config_no_mcp_servers(self, tmp_path: Path) -> None:
        """Test reading config without mcpServers key."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"otherKey": "value"}')
        manager = MCPConfigManager()
        result = manager.read_existing_config(config_path)
        assert "mcpServers" in result
        assert result["otherKey"] == "value"

    def test_read_existing_config_invalid_json(self, tmp_path: Path) -> None:
        """Test reading invalid JSON raises error."""
        config_path = tmp_path / "config.json"
        config_path.write_text("not valid json {")
        manager = MCPConfigManager()
        with pytest.raises(ConfigError) as exc_info:
            manager.read_existing_config(config_path)
        assert "Invalid JSON" in str(exc_info.value)

    def test_merge_config_preserves_other_servers(self) -> None:
        """Test merge preserves other MCP servers."""
        manager = MCPConfigManager()
        existing: dict[str, object] = {"mcpServers": {"other-tool": {"command": "other"}}}
        new: dict[str, object] = {
            "mcpServers": {"tg-parser": {"command": "uvx", "args": ["tg-parser"]}}
        }

        result = manager.merge_config(existing, new)

        mcp_servers = cast(dict[str, Any], result["mcpServers"])
        assert "other-tool" in mcp_servers
        assert "tg-parser" in mcp_servers

    def test_merge_config_overwrites_existing_entry(self) -> None:
        """Test merge overwrites existing tg-parser entry."""
        manager = MCPConfigManager()
        existing: dict[str, object] = {"mcpServers": {"tg-parser": {"command": "old"}}}
        new: dict[str, object] = {"mcpServers": {"tg-parser": {"command": "new"}}}

        result = manager.merge_config(existing, new)

        mcp_servers = cast(dict[str, Any], result["mcpServers"])
        assert mcp_servers["tg-parser"]["command"] == "new"

    def test_merge_config_creates_mcp_servers_if_missing(self) -> None:
        """Test merge creates mcpServers if missing in existing."""
        manager = MCPConfigManager()
        existing: dict[str, object] = {"otherKey": "value"}
        new: dict[str, object] = {"mcpServers": {"tg-parser": {"command": "uvx"}}}

        result = manager.merge_config(existing, new)

        assert "mcpServers" in result
        mcp_servers = cast(dict[str, Any], result["mcpServers"])
        assert "tg-parser" in mcp_servers
        assert result["otherKey"] == "value"

    def test_create_backup(self, tmp_path: Path) -> None:
        """Test backup creation."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"test": true}')

        manager = MCPConfigManager()
        backup_path = manager.create_backup(config_path)

        assert backup_path is not None
        assert backup_path.exists()
        assert ".backup" in backup_path.suffix
        assert backup_path.read_text() == '{"test": true}'

    def test_create_backup_nonexistent_file(self, tmp_path: Path) -> None:
        """Test backup returns None for nonexistent file."""
        manager = MCPConfigManager()
        result = manager.create_backup(tmp_path / "nonexistent.json")
        assert result is None

    def test_apply_config_creates_new(self, tmp_path: Path) -> None:
        """Test applying config creates new file."""
        manager = MCPConfigManager()
        config_path = tmp_path / "claude" / "config.json"

        with patch.object(manager, "get_config_path", return_value=config_path):
            with patch.object(manager, "is_in_venv", return_value=False):
                result = manager.apply_config()

        assert result.created_new is True
        assert config_path.exists()
        content = json.loads(config_path.read_text())
        assert "tg-parser" in content["mcpServers"]

    def test_apply_config_updates_existing(self, tmp_path: Path) -> None:
        """Test applying config updates existing entry."""
        config_path = tmp_path / "claude" / "config.json"
        config_path.parent.mkdir(parents=True)
        existing = {"mcpServers": {"tg-parser": {"command": "old"}}}
        config_path.write_text(json.dumps(existing))

        manager = MCPConfigManager()
        with patch.object(manager, "get_config_path", return_value=config_path):
            with patch.object(manager, "is_in_venv", return_value=False):
                result = manager.apply_config(create_backup=False)

        assert result.updated_existing is True
        content = json.loads(config_path.read_text())
        assert content["mcpServers"]["tg-parser"]["command"] == "uvx"

    def test_apply_config_dry_run(self, tmp_path: Path) -> None:
        """Test dry run doesn't write file."""
        config_path = tmp_path / "config.json"
        manager = MCPConfigManager()

        with patch.object(manager, "get_config_path", return_value=config_path):
            with patch.object(manager, "is_in_venv", return_value=False):
                result = manager.apply_config(dry_run=True)

        assert not config_path.exists()
        assert result.created_new is True

    def test_apply_config_creates_backup(self, tmp_path: Path) -> None:
        """Test apply creates backup when file exists."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"mcpServers": {}}')

        manager = MCPConfigManager()
        with patch.object(manager, "get_config_path", return_value=config_path):
            with patch.object(manager, "is_in_venv", return_value=False):
                result = manager.apply_config(create_backup=True)

        assert result.backup_path is not None
        assert result.backup_path.exists()

    def test_apply_config_no_backup(self, tmp_path: Path) -> None:
        """Test apply without backup."""
        config_path = tmp_path / "config.json"
        config_path.write_text('{"mcpServers": {}}')

        manager = MCPConfigManager()
        with patch.object(manager, "get_config_path", return_value=config_path):
            with patch.object(manager, "is_in_venv", return_value=False):
                result = manager.apply_config(create_backup=False)

        assert result.backup_path is None

    def test_apply_config_preserves_other_servers(self, tmp_path: Path) -> None:
        """Test apply preserves other MCP servers."""
        config_path = tmp_path / "config.json"
        existing = {"mcpServers": {"other-tool": {"command": "other"}}}
        config_path.write_text(json.dumps(existing))

        manager = MCPConfigManager()
        with patch.object(manager, "get_config_path", return_value=config_path):
            with patch.object(manager, "is_in_venv", return_value=False):
                manager.apply_config(create_backup=False)

        content = json.loads(config_path.read_text())
        assert "other-tool" in content["mcpServers"]
        assert "tg-parser" in content["mcpServers"]

    def test_apply_config_use_uv_run(self, tmp_path: Path) -> None:
        """Test apply config with uv run option."""
        config_path = tmp_path / "config.json"
        manager = MCPConfigManager()

        with patch.object(manager, "get_config_path", return_value=config_path):
            with patch.object(manager, "is_in_venv", return_value=False):
                manager.apply_config(use_uv_run=True)

        content = json.loads(config_path.read_text())
        assert content["mcpServers"]["tg-parser"]["command"] == "uv"
        assert content["mcpServers"]["tg-parser"]["args"] == ["run", "tg-parser", "mcp"]
