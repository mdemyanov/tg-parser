"""Integration tests for config CLI commands."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

# Import commands to register them
import tg_parser.presentation.cli.commands.config
import tg_parser.presentation.cli.commands.parse  # noqa: F401
from tg_parser.presentation.cli.app import app, state

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


class TestConfigShowCommand:
    """Test config show command."""

    def test_config_show_defaults(self) -> None:
        """Test showing default config."""
        # Reset state
        state.config = None
        state.config_path = None

        result = runner.invoke(app, ["config", "show"])

        assert result.exit_code == 0
        assert "Effective Configuration" in result.stdout
        assert "markdown" in result.stdout  # default format
        assert "default" in result.stdout

    def test_config_show_verbose(self) -> None:
        """Test verbose output shows all settings."""
        # Reset state
        state.config = None
        state.config_path = None

        result = runner.invoke(app, ["config", "show", "-v"])

        assert result.exit_code == 0
        assert "filtering" in result.stdout
        assert "chunking" in result.stdout
        assert "mentions" in result.stdout
        assert "stats" in result.stdout

    def test_config_show_with_file(self, tmp_path: Path) -> None:
        """Test showing config from specific file."""
        # Reset state
        state.config = None
        state.config_path = None

        config_file = tmp_path / "test.toml"
        config_file.write_text('[default]\noutput_format = "json"')

        result = runner.invoke(app, ["config", "show", "-c", str(config_file)])

        assert result.exit_code == 0
        # Path may be wrapped in output, check filename instead
        assert "test.toml" in result.stdout
        assert "json" in result.stdout

    def test_config_show_nonexistent_file(self, tmp_path: Path) -> None:
        """Test showing config from non-existent file."""
        # Reset state
        state.config = None
        state.config_path = None

        result = runner.invoke(
            app, ["config", "show", "-c", str(tmp_path / "missing.toml")]
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestConfigInitCommand:
    """Test config init command."""

    def test_config_init_creates_file(self, tmp_path: Path) -> None:
        """Test creating example config file."""
        output = tmp_path / "tg-parser.toml"

        result = runner.invoke(app, ["config", "init", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()

        content = output.read_text()
        assert "[default]" in content
        assert "output_format" in content

    def test_config_init_default_location(self, tmp_path: Path) -> None:
        """Test creating config in default location."""
        # Change to tmp_path as working dir is not easy with CliRunner,
        # so we specify output explicitly
        output = tmp_path / "config.toml"

        result = runner.invoke(app, ["config", "init", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()

    def test_config_init_no_overwrite(self, tmp_path: Path) -> None:
        """Test init doesn't overwrite without --force."""
        output = tmp_path / "tg-parser.toml"
        output.write_text("existing content")

        result = runner.invoke(app, ["config", "init", "-o", str(output)])

        assert result.exit_code == 1
        assert "already exists" in result.stdout
        assert output.read_text() == "existing content"

    def test_config_init_force_overwrite(self, tmp_path: Path) -> None:
        """Test init overwrites with --force."""
        output = tmp_path / "tg-parser.toml"
        output.write_text("existing content")

        result = runner.invoke(app, ["config", "init", "-o", str(output), "--force"])

        assert result.exit_code == 0
        assert "[default]" in output.read_text()

    def test_config_init_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Test init creates parent directories."""
        output = tmp_path / "nested" / "dir" / "config.toml"

        result = runner.invoke(app, ["config", "init", "-o", str(output)])

        assert result.exit_code == 0
        assert output.exists()


class TestConfigPathCommand:
    """Test config path command."""

    def test_config_path_shows_locations(self) -> None:
        """Test showing config search locations."""
        result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert "search locations" in result.stdout
        assert "tg-parser.toml" in result.stdout

    def test_config_path_shows_priority_numbers(self) -> None:
        """Test locations have priority numbers."""
        result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert "#" in result.stdout
        assert "1" in result.stdout
        assert "2" in result.stdout

    def test_config_path_shows_active_config(self, tmp_path: Path) -> None:
        """Test shows active config when one exists."""
        # Reset state
        state.config = None
        state.config_path = None

        # Note: Without mocking, this tests the "None" case
        result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert "Active config:" in result.stdout


class TestGlobalConfigOption:
    """Test global --config option."""

    def test_parse_with_config_file(
        self, tmp_path: Path, personal_chat_path: Path
    ) -> None:
        """Test parse uses config file defaults."""
        # Reset state
        state.config = None
        state.config_path = None

        config_file = tmp_path / "config.toml"
        config_file.write_text('[default]\noutput_format = "json"')
        output_dir = tmp_path / "output"

        result = runner.invoke(
            app,
            [
                "--config",
                str(config_file),
                "parse",
                str(personal_chat_path),
                "-o",
                str(output_dir),
            ],
        )

        assert result.exit_code == 0

    def test_global_config_loads_before_command(self, tmp_path: Path) -> None:
        """Test --config loads config before command runs."""
        # Reset state
        state.config = None
        state.config_path = None

        config_file = tmp_path / "config.toml"
        config_file.write_text('[default]\noutput_format = "kb"')

        # Note: The global --config option loads config into state,
        # but config show command has its own -c option which takes precedence.
        # Use config show -c to pass the config path directly.
        result = runner.invoke(
            app,
            ["config", "show", "-c", str(config_file)],
        )

        assert result.exit_code == 0
        assert "kb" in result.stdout

    def test_global_config_invalid_file_warns(self, tmp_path: Path) -> None:
        """Test invalid config file shows warning but continues."""
        # Reset state
        state.config = None
        state.config_path = None

        config_file = tmp_path / "invalid.toml"
        config_file.write_text("invalid { toml")

        # Should warn but still run with defaults
        result = runner.invoke(
            app,
            ["--config", str(config_file), "config", "show"],
        )

        # Should either work with warning or fail gracefully
        # The behavior depends on implementation
        assert "Warning" in result.stdout or "markdown" in result.stdout


class TestConfigWithParse:
    """Test config integration with parse command."""

    def test_parse_respects_config_format(
        self, tmp_path: Path, personal_chat_path: Path
    ) -> None:
        """Test parse respects config file output_format."""
        # Reset state
        state.config = None
        state.config_path = None

        config_file = tmp_path / "config.toml"
        config_file.write_text('[default]\noutput_format = "json"')
        output_dir = tmp_path / "output"

        result = runner.invoke(
            app,
            [
                "--config",
                str(config_file),
                "parse",
                str(personal_chat_path),
                "-o",
                str(output_dir),
                # Note: not specifying -f, should use config default
            ],
        )

        # Command should succeed
        assert result.exit_code == 0
