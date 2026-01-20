"""Integration tests for CLI."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

# Import commands to register them
import tg_parser.presentation.cli.commands.chunk
import tg_parser.presentation.cli.commands.mentions
import tg_parser.presentation.cli.commands.parse
import tg_parser.presentation.cli.commands.stats  # noqa: F401
from tg_parser.presentation.cli.app import app

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


class TestParseCommand:
    """Test parse CLI command."""

    def test_parse_personal_chat(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parsing personal chat."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            ["parse", str(personal_chat_path), "-o", str(output_dir)],
        )
        assert result.exit_code == 0
        assert "Parsed" in result.stdout
        assert "messages" in result.stdout

        # Check output file created
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 1

    def test_parse_with_verbose(self, personal_chat_path: Path, tmp_path: Path) -> None:
        """Test parse with verbose flag."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            ["parse", str(personal_chat_path), "-o", str(output_dir), "-v"],
        )
        assert result.exit_code == 0
        assert "Chat type:" in result.stdout
        assert "Participants:" in result.stdout

    def test_parse_with_sender_filter(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse with sender filter."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(output_dir),
                "--senders",
                "Alice",
            ],
        )
        assert result.exit_code == 0
        # Should have fewer messages
        assert "Parsed" in result.stdout

    def test_parse_nonexistent_file(self, tmp_path: Path) -> None:
        """Test parse with nonexistent file."""
        result = runner.invoke(
            app,
            ["parse", str(tmp_path / "nonexistent.json")],
        )
        assert result.exit_code != 0

    def test_parse_invalid_format(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse with invalid format."""
        result = runner.invoke(
            app,
            ["parse", str(personal_chat_path), "-f", "invalid"],
        )
        assert result.exit_code != 0
        assert "Unsupported format" in result.stdout

    def test_parse_kb_format(self, personal_chat_path: Path, tmp_path: Path) -> None:
        """Test parsing with KB format produces YAML frontmatter."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            ["parse", str(personal_chat_path), "-o", str(output_dir), "-f", "kb"],
        )
        assert result.exit_code == 0
        assert "Parsed" in result.stdout

        # Check output file created
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 1

        # Check KB format features
        content = output_files[0].read_text(encoding="utf-8")
        assert content.startswith("---\n")  # YAML frontmatter
        assert "title:" in content
        assert "chat_type:" in content
        assert "participants:" in content
        assert "estimated_tokens:" in content
        assert "tags:" in content
        assert "telegram-export" in content
        # WikiLinks in headers
        assert "[[user" in content

    def test_parse_json_format(self, personal_chat_path: Path, tmp_path: Path) -> None:
        """Test parsing with JSON format produces valid JSON."""
        import json

        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            ["parse", str(personal_chat_path), "-o", str(output_dir), "-f", "json"],
        )
        assert result.exit_code == 0
        assert "Parsed" in result.stdout

        # Check output file created
        output_files = list(output_dir.glob("*.json"))
        assert len(output_files) == 1

        # Check valid JSON
        content = output_files[0].read_text(encoding="utf-8")
        data = json.loads(content)
        assert "meta" in data
        assert "messages" in data
        assert "participants" in data
        assert data["meta"]["chat_name"] == "Test User"

    def test_parse_kb_no_frontmatter(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parsing with KB format and --no-frontmatter flag."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(output_dir),
                "-f",
                "kb",
                "--no-frontmatter",
            ],
        )
        assert result.exit_code == 0
        assert "Parsed" in result.stdout

        # Check output file created
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) == 1

        # Check NO YAML frontmatter (should be plain markdown)
        content = output_files[0].read_text(encoding="utf-8")
        assert not content.startswith("---\n")
        assert "# Chat:" in content

    def test_parse_help_shows_formats(self) -> None:
        """Test that parse help shows all available formats."""
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0
        assert "markdown" in result.stdout
        assert "kb" in result.stdout
        assert "json" in result.stdout


class TestStatsCommand:
    """Test stats CLI command."""

    def test_stats_personal_chat(self, personal_chat_path: Path) -> None:
        """Test stats on personal chat."""
        result = runner.invoke(app, ["stats", str(personal_chat_path)])
        assert result.exit_code == 0
        assert "Test User" in result.stdout
        assert "Messages" in result.stdout
        assert "Participants" in result.stdout

    def test_stats_with_top_senders(self, supergroup_with_topics_path: Path) -> None:
        """Test stats with custom top senders count."""
        result = runner.invoke(
            app,
            ["stats", str(supergroup_with_topics_path), "--top-senders", "5"],
        )
        assert result.exit_code == 0
        assert "Top Senders" in result.stdout

    def test_stats_shows_topics(self, supergroup_with_topics_path: Path) -> None:
        """Test stats shows topics for forum."""
        result = runner.invoke(app, ["stats", str(supergroup_with_topics_path)])
        assert result.exit_code == 0
        assert "Topics" in result.stdout
        assert "General" in result.stdout or "Finances" in result.stdout


class TestVersionCommand:
    """Test version command."""

    def test_version_flag(self) -> None:
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "tg-parser version" in result.stdout

    def test_short_version_flag(self) -> None:
        """Test -V flag."""
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "tg-parser version" in result.stdout


class TestHelpCommand:
    """Test help output."""

    def test_main_help(self) -> None:
        """Test main help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "parse" in result.stdout
        assert "stats" in result.stdout

    def test_parse_help(self) -> None:
        """Test parse command help."""
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.stdout
        assert "--date-from" in result.stdout
        assert "--senders" in result.stdout

    def test_stats_help(self) -> None:
        """Test stats command help."""
        result = runner.invoke(app, ["stats", "--help"])
        assert result.exit_code == 0
        assert "--top-senders" in result.stdout

    def test_chunk_help(self) -> None:
        """Test chunk command help."""
        result = runner.invoke(app, ["chunk", "--help"])
        assert result.exit_code == 0
        assert "--strategy" in result.stdout
        assert "--max-tokens" in result.stdout


class TestChunkCommand:
    """Test chunk CLI command."""

    def test_chunk_fixed_strategy(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test fixed chunking strategy."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-s",
                "fixed",
                "-t",
                "1000",
            ],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout
        # Check output files exist
        assert any(output_dir.glob("chunk_*.md"))

    def test_chunk_topic_strategy(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test topic chunking strategy."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-s",
                "topic",
            ],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    def test_chunk_hybrid_strategy(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test hybrid chunking strategy."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-s",
                "hybrid",
                "-t",
                "500",
            ],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    def test_chunk_single_file_output(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test single file output mode."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--single-file",
            ],
        )
        assert result.exit_code == 0
        assert (output_dir / "chunks.md").exists()

    def test_chunk_verbose_output(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test verbose output shows chunk details."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-v",
            ],
        )
        assert result.exit_code == 0
        # Verbose should show table with chunk details
        assert "Messages" in result.stdout or "Tokens" in result.stdout

    def test_chunk_invalid_strategy(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test error on invalid strategy."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "-s",
                "invalid",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid strategy" in result.stdout

    def test_chunk_file_not_found(self, tmp_path: Path) -> None:
        """Test error when input file not found."""
        result = runner.invoke(
            app,
            [
                "chunk",
                str(tmp_path / "nonexistent.json"),
                "-o",
                str(tmp_path / "chunks"),
            ],
        )
        assert result.exit_code != 0

    def test_chunk_personal_chat(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test chunking personal chat."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(personal_chat_path),
                "-o",
                str(output_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout


class TestTopicFiltering:
    """Test topic filtering CLI options."""

    def test_parse_with_topics_filter(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test parse with topic filter."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--topics",
                "Finances",
            ],
        )
        assert result.exit_code == 0
        content = (output_dir / "Test_Group.md").read_text()
        # Should only have Finances topic messages
        assert "Budget discussion" in content or "finance talk" in content
        # Should NOT have General topic messages
        assert "Hello in General topic" not in content

    def test_parse_with_exclude_topics(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test parse with exclude topics."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--exclude-topics",
                "General",
            ],
        )
        assert result.exit_code == 0
        content = (output_dir / "Test_Group.md").read_text()
        # Should NOT have General topic messages
        assert "Hello in General topic" not in content

    def test_parse_split_topics(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test --split-topics creates separate files."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--split-topics",
            ],
        )
        assert result.exit_code == 0
        assert "Split" in result.stdout
        assert "files" in result.stdout

        # Check files created
        output_files = list(output_dir.glob("*.md"))
        assert len(output_files) >= 2  # At least General and Finances

        # Check expected files exist
        filenames = {f.stem for f in output_files}
        assert (
            "General" in filenames
            or "Finances" in filenames
            or "_no_topic" in filenames
        )

    def test_parse_split_topics_verbose(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test --split-topics with verbose shows file details."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--split-topics",
                "-v",
            ],
        )
        assert result.exit_code == 0
        # Verbose shows table with file counts
        assert "Messages" in result.stdout

    def test_parse_split_topics_with_sender_filter(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test --split-topics combined with sender filter."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--split-topics",
                "--senders",
                "User1",
            ],
        )
        assert result.exit_code == 0
        # Should only have User1's messages split by topic
        assert "Split" in result.stdout

    def test_parse_help_shows_topic_options(self) -> None:
        """Test that parse help shows topic filter options."""
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0
        assert "--topics" in result.stdout
        assert "--exclude-topics" in result.stdout
        assert "--split-topics" in result.stdout


class TestMentionsCommand:
    """Test mentions CLI command."""

    def test_mentions_basic(self, supergroup_with_topics_path: Path) -> None:
        """Test basic mentions output."""
        result = runner.invoke(app, ["mentions", str(supergroup_with_topics_path)])
        assert result.exit_code == 0
        # Should show mentions info or "No mentions found"
        assert (
            "Total mentions:" in result.stdout or "No mentions found" in result.stdout
        )

    def test_mentions_json_format(self, supergroup_with_topics_path: Path) -> None:
        """Test JSON output format."""
        import json

        result = runner.invoke(
            app,
            ["mentions", str(supergroup_with_topics_path), "-f", "json"],
        )
        assert result.exit_code == 0

        data = json.loads(result.stdout)
        assert "total_mentions" in data
        assert "unique_users" in data
        assert "mentions" in data
        assert "chat_name" in data

    def test_mentions_with_min_count(self, supergroup_with_topics_path: Path) -> None:
        """Test min-count filter."""
        result = runner.invoke(
            app,
            ["mentions", str(supergroup_with_topics_path), "--min-count", "5"],
        )
        assert result.exit_code == 0

    def test_mentions_with_date_filter(self, supergroup_with_topics_path: Path) -> None:
        """Test date range filter."""
        result = runner.invoke(
            app,
            [
                "mentions",
                str(supergroup_with_topics_path),
                "--date-from",
                "2025-01-01",
                "--date-to",
                "2025-12-31",
            ],
        )
        assert result.exit_code == 0

    def test_mentions_help(self) -> None:
        """Test mentions command help."""
        result = runner.invoke(app, ["mentions", "--help"])
        assert result.exit_code == 0
        assert "--min-count" in result.stdout
        assert "--format" in result.stdout
        assert "--date-from" in result.stdout


class TestExtractionGuideFlag:
    """Test --include-extraction-guide flag."""

    def test_parse_with_extraction_guide(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse includes extraction guide."""
        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(output_dir),
                "--include-extraction-guide",
            ],
        )
        assert result.exit_code == 0

        output_file = list(output_dir.glob("*.md"))[0]
        content = output_file.read_text(encoding="utf-8")
        assert "Инструкция по извлечению артефактов" in content
        assert "Решения" in content
        assert "Блокеры" in content

    def test_parse_json_with_extraction_guide(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse JSON includes extraction guide in meta."""
        import json

        output_dir = tmp_path / "output"
        result = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(output_dir),
                "-f",
                "json",
                "--include-extraction-guide",
            ],
        )
        assert result.exit_code == 0

        output_file = list(output_dir.glob("*.json"))[0]
        content = output_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert "extraction_guide" in data["meta"]
        assert "Инструкция" in data["meta"]["extraction_guide"]

    def test_chunk_with_extraction_guide(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test chunk includes extraction guide."""
        output_dir = tmp_path / "chunks"
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(output_dir),
                "--single-file",
                "--include-extraction-guide",
            ],
        )
        assert result.exit_code == 0

        output_file = output_dir / "chunks.md"
        content = output_file.read_text(encoding="utf-8")
        assert "Инструкция по извлечению артефактов" in content

    def test_parse_help_shows_extraction_guide_option(self) -> None:
        """Test that parse help shows extraction guide option."""
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0
        # Use partial match because Rich may truncate long option names
        assert "--include-extraction" in result.stdout

    def test_chunk_help_shows_extraction_guide_option(self) -> None:
        """Test that chunk help shows extraction guide option."""
        result = runner.invoke(app, ["chunk", "--help"])
        assert result.exit_code == 0
        # Use partial match because Rich may truncate long option names
        assert "--include-extraction" in result.stdout
