"""Integration tests for split-topics CLI command."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

# Import commands to register them
import tg_parser.presentation.cli.commands.split_topics  # noqa: F401
from tg_parser.presentation.cli.app import app

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


class TestSplitTopicsCommand:
    """Test split-topics CLI command."""

    def test_split_topics_with_forum(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test splitting a chat with topics."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            ["split-topics", str(supergroup_with_topics_path), "-o", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "Split" in result.stdout
        assert "files" in result.stdout

        # Check multiple output files created
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) >= 2

    def test_split_topics_verbose(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test split-topics with verbose flag."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            [
                "split-topics",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-v",
            ],
        )
        assert result.exit_code == 0
        assert "Files Created" in result.stdout
        assert "Messages" in result.stdout

    def test_split_topics_without_topics(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test splitting a chat without topics (all go to _no_topic)."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            ["split-topics", str(personal_chat_path), "-o", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "Split" in result.stdout

        # Check only one output file created (_no_topic)
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 1
        assert output_files[0].name == "_no_topic.md"

    def test_split_topics_json_format(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test split-topics with JSON output format."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            [
                "split-topics",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-f",
                "json",
            ],
        )
        assert result.exit_code == 0

        # Check JSON files created
        output_files = list(output_dir.glob("*.json"))
        assert len(output_files) >= 2

    def test_split_topics_kb_format(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test split-topics with KB template format."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            [
                "split-topics",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-f",
                "kb",
            ],
        )
        assert result.exit_code == 0

        # Check markdown files created with frontmatter
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) >= 2

        # Check one file has frontmatter
        content = output_files[0].read_text(encoding="utf-8")
        assert content.startswith("---")

    def test_split_topics_no_frontmatter(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test split-topics with --no-frontmatter flag."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            [
                "split-topics",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-f",
                "kb",
                "--no-frontmatter",
            ],
        )
        assert result.exit_code == 0

        # Check markdown files created without frontmatter
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) >= 2

        # Check file does not start with frontmatter marker
        content = output_files[0].read_text(encoding="utf-8")
        assert not content.startswith("---")

    def test_split_topics_with_extraction_guide(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test split-topics with extraction guide."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            [
                "split-topics",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--include-extraction-guide",
            ],
        )
        assert result.exit_code == 0

        # Check output file contains extraction guide
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) >= 1

        content = output_files[0].read_text(encoding="utf-8")
        assert "Инструкция по извлечению артефактов" in content

    def test_split_topics_help(self) -> None:
        """Test split-topics help shows all options."""
        result = runner.invoke(app, ["split-topics", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.stdout
        assert "--format" in result.stdout
        assert "--no-frontmatter" in result.stdout
        # Use partial match for potentially truncated option name
        assert "--include-extraction" in result.stdout
        assert "--streaming" in result.stdout
        assert "--verbose" in result.stdout

    def test_split_topics_invalid_format(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test split-topics with invalid format."""
        output_dir = tmp_path / "topics"
        result = runner.invoke(
            app,
            [
                "split-topics",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-f",
                "invalid",
            ],
        )
        assert result.exit_code == 1
        assert "Unsupported format" in result.stdout

    def test_split_topics_file_not_found(self, tmp_path: Path) -> None:
        """Test split-topics with non-existent file."""
        result = runner.invoke(
            app,
            ["split-topics", str(tmp_path / "nonexistent.json")],
        )
        assert result.exit_code != 0
