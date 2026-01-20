"""Integration tests for mcp-config CLI command."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

# Import command to register it
import tg_parser.presentation.cli.commands.mcp_config  # noqa: F401
from tg_parser.presentation.cli.app import app

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


class TestMCPConfigCommand:
    """Test mcp-config CLI command."""

    def test_mcp_config_prints_json(self) -> None:
        """Test default behavior prints JSON config."""
        result = runner.invoke(app, ["mcp-config"])
        assert result.exit_code == 0
        # Output should contain mcpServers
        assert "mcpServers" in result.stdout
        assert "tg-parser" in result.stdout

    def test_mcp_config_verbose(self) -> None:
        """Test verbose output shows additional info."""
        result = runner.invoke(app, ["mcp-config", "-v"])
        assert result.exit_code == 0
        assert "Environment:" in result.stdout
        assert "Command:" in result.stdout

    def test_mcp_config_dry_run(self, tmp_path: Path) -> None:
        """Test dry run shows what would be written."""
        config_path = tmp_path / "claude" / "config.json"

        with patch(
            "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.get_config_path",
            return_value=config_path,
        ):
            result = runner.invoke(app, ["mcp-config", "--apply", "--dry-run"])

        assert result.exit_code == 0
        assert "Dry run" in result.stdout or "Would" in result.stdout
        # File should NOT be created
        assert not config_path.exists()

    def test_mcp_config_apply_creates_file(self, tmp_path: Path) -> None:
        """Test apply creates config file."""
        config_path = tmp_path / "claude" / "config.json"

        with patch(
            "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.get_config_path",
            return_value=config_path,
        ):
            result = runner.invoke(app, ["mcp-config", "--apply", "--no-backup"])

        assert result.exit_code == 0
        assert "Success" in result.stdout
        assert config_path.exists()

        content = json.loads(config_path.read_text())
        assert "mcpServers" in content
        assert "tg-parser" in content["mcpServers"]

    def test_mcp_config_apply_preserves_existing(self, tmp_path: Path) -> None:
        """Test apply preserves existing MCP servers."""
        config_path = tmp_path / "claude" / "config.json"
        config_path.parent.mkdir(parents=True)
        existing = {"mcpServers": {"other-tool": {"command": "other"}}}
        config_path.write_text(json.dumps(existing))

        with patch(
            "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.get_config_path",
            return_value=config_path,
        ):
            result = runner.invoke(app, ["mcp-config", "--apply", "--no-backup"])

        assert result.exit_code == 0

        content = json.loads(config_path.read_text())
        assert "other-tool" in content["mcpServers"]
        assert "tg-parser" in content["mcpServers"]

    def test_mcp_config_apply_creates_backup(self, tmp_path: Path) -> None:
        """Test apply creates backup by default."""
        config_path = tmp_path / "claude" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('{"mcpServers": {}}')

        with patch(
            "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.get_config_path",
            return_value=config_path,
        ):
            result = runner.invoke(app, ["mcp-config", "--apply"])

        assert result.exit_code == 0
        assert "Backup" in result.stdout or "backup" in result.stdout

        # Check backup file exists
        backup_files = list(config_path.parent.glob("*.backup"))
        assert len(backup_files) == 1

    def test_mcp_config_help(self) -> None:
        """Test help output."""
        result = runner.invoke(app, ["mcp-config", "--help"])
        assert result.exit_code == 0
        assert "--apply" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--target" in result.stdout
        assert "desktop" in result.stdout

    def test_mcp_config_target_code(self) -> None:
        """Test target code option is accepted."""
        result = runner.invoke(app, ["mcp-config", "--target", "code"])
        assert result.exit_code == 0
        assert "mcpServers" in result.stdout

    def test_mcp_config_use_uv_run(self) -> None:
        """Test --use-uv-run option when not in venv."""
        with patch(
            "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.is_in_venv",
            return_value=False,
        ):
            result = runner.invoke(app, ["mcp-config", "--use-uv-run"])
        assert result.exit_code == 0
        assert "uv" in result.stdout
        assert "run" in result.stdout

    def test_mcp_config_apply_with_use_uv_run(self, tmp_path: Path) -> None:
        """Test apply with --use-uv-run option when not in venv."""
        config_path = tmp_path / "config.json"

        with patch(
            "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.get_config_path",
            return_value=config_path,
        ):
            with patch(
                "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.is_in_venv",
                return_value=False,
            ):
                result = runner.invoke(
                    app, ["mcp-config", "--apply", "--no-backup", "--use-uv-run"]
                )

        assert result.exit_code == 0
        assert config_path.exists()

        content = json.loads(config_path.read_text())
        assert content["mcpServers"]["tg-parser"]["command"] == "uv"
        assert content["mcpServers"]["tg-parser"]["args"] == ["run", "tg-parser", "mcp"]

    def test_mcp_config_dry_run_verbose(self, tmp_path: Path) -> None:
        """Test dry run with verbose output."""
        config_path = tmp_path / "config.json"

        with patch(
            "tg_parser.infrastructure.config.mcp_config_manager.MCPConfigManager.get_config_path",
            return_value=config_path,
        ):
            result = runner.invoke(app, ["mcp-config", "--apply", "--dry-run", "-v"])

        assert result.exit_code == 0
        assert "Dry run" in result.stdout
        assert "Environment:" in result.stdout
        assert "Target file:" in result.stdout
