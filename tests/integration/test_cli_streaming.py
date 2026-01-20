"""Integration tests for CLI streaming functionality."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

# Import commands to register them with the app
import tg_parser.presentation.cli.commands.chunk
import tg_parser.presentation.cli.commands.parse  # noqa: F401
from tg_parser.infrastructure.readers import is_ijson_available
from tg_parser.presentation.cli.app import app

runner = CliRunner(env={"NO_COLOR": "1", "TERM": "dumb"})


class TestParseCommandStreaming:
    """Test parse command with streaming options."""

    def test_parse_default_mode(self, personal_chat_path: Path, tmp_path: Path) -> None:
        """Test parse command with default (auto) streaming mode."""
        result = runner.invoke(
            app, ["parse", str(personal_chat_path), "-o", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    def test_parse_no_streaming_flag(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse command with --no-streaming flag."""
        result = runner.invoke(
            app,
            ["parse", str(personal_chat_path), "-o", str(tmp_path), "--no-streaming"],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_parse_streaming_flag(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse command with --streaming flag."""
        result = runner.invoke(
            app, ["parse", str(personal_chat_path), "-o", str(tmp_path), "--streaming"]
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    @pytest.mark.skipif(is_ijson_available(), reason="ijson is installed")
    def test_parse_streaming_flag_without_ijson(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test --streaming flag shows error when ijson not installed."""
        result = runner.invoke(
            app, ["parse", str(personal_chat_path), "-o", str(tmp_path), "--streaming"]
        )
        # Should fail with missing dependency error
        assert result.exit_code == 1
        assert "dependency" in result.stdout.lower() or "ijson" in result.stdout.lower()

    def test_parse_output_same_with_both_modes(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test output is same with and without streaming."""
        if not is_ijson_available():
            pytest.skip("ijson not installed")

        # Parse without streaming
        no_stream_out = tmp_path / "no_stream"
        result1 = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(no_stream_out),
                "--no-streaming",
            ],
        )
        assert result1.exit_code == 0

        # Parse with streaming
        stream_out = tmp_path / "stream"
        result2 = runner.invoke(
            app,
            ["parse", str(personal_chat_path), "-o", str(stream_out), "--streaming"],
        )
        assert result2.exit_code == 0

        # Find output files
        no_stream_files = list(no_stream_out.glob("*.md"))
        stream_files = list(stream_out.glob("*.md"))

        assert len(no_stream_files) == 1
        assert len(stream_files) == 1

        # Compare content
        no_stream_content = no_stream_files[0].read_text()
        stream_content = stream_files[0].read_text()

        # Content should be identical
        assert no_stream_content == stream_content


class TestChunkCommandStreaming:
    """Test chunk command with streaming options."""

    def test_chunk_default_mode(self, personal_chat_path: Path, tmp_path: Path) -> None:
        """Test chunk command with default (auto) streaming mode."""
        result = runner.invoke(
            app, ["chunk", str(personal_chat_path), "-o", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    def test_chunk_no_streaming_flag(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test chunk command with --no-streaming flag."""
        result = runner.invoke(
            app,
            ["chunk", str(personal_chat_path), "-o", str(tmp_path), "--no-streaming"],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_chunk_streaming_flag(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test chunk command with --streaming flag."""
        result = runner.invoke(
            app, ["chunk", str(personal_chat_path), "-o", str(tmp_path), "--streaming"]
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    def test_chunk_with_strategy(
        self, supergroup_with_topics_path: Path, tmp_path: Path
    ) -> None:
        """Test chunk with topic strategy and streaming."""
        result = runner.invoke(
            app,
            [
                "chunk",
                str(supergroup_with_topics_path),
                "-o",
                str(tmp_path),
                "-s",
                "topic",
                "--no-streaming",
            ],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout


class TestStreamingWithFilters:
    """Test streaming mode works correctly with filters."""

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_parse_with_date_filter_streaming(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse with date filter and streaming."""
        result = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(tmp_path),
                "--streaming",
                "--date-from",
                "2024-01-15",
            ],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_parse_with_sender_filter_streaming(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test parse with sender filter and streaming."""
        result = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(tmp_path),
                "--streaming",
                "--senders",
                "Alice",
            ],
        )
        assert result.exit_code == 0
        assert "Success" in result.stdout


class TestStreamingVerboseMode:
    """Test streaming with verbose output."""

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_parse_streaming_verbose(
        self, personal_chat_path: Path, tmp_path: Path
    ) -> None:
        """Test verbose output with streaming."""
        result = runner.invoke(
            app,
            [
                "parse",
                str(personal_chat_path),
                "-o",
                str(tmp_path),
                "--streaming",
                "-v",
            ],
        )
        assert result.exit_code == 0
        # Verbose should show chat type
        assert "personal" in result.stdout.lower() or "Success" in result.stdout
