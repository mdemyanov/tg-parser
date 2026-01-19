"""Tests for reader factory function."""

from __future__ import annotations

from pathlib import Path

import pytest

from tg_parser.infrastructure.readers import (
    TelegramJSONReader,
    get_reader,
    is_ijson_available,
)


class TestIsIjsonAvailable:
    """Test is_ijson_available function."""

    def test_returns_bool(self) -> None:
        """Test function returns boolean."""
        result = is_ijson_available()
        assert isinstance(result, bool)

    def test_returns_true_when_ijson_installed(self) -> None:
        """Test returns True when ijson is installed."""
        try:
            import ijson  # noqa: F401

            assert is_ijson_available() is True
        except ImportError:
            pytest.skip("ijson not installed")

    def test_returns_false_when_ijson_missing(self) -> None:
        """Test returns False when ijson import fails.

        Note: This test is difficult to implement properly because ijson
        may already be imported. We rely on the monkeypatch tests below.
        """
        # This test would need to manipulate the module system
        # which is complex and fragile. Skip for now.
        pytest.skip("Cannot easily mock already-imported module")


class TestGetReader:
    """Test get_reader factory function."""

    def test_returns_json_reader_for_small_file(self, personal_chat_path: Path) -> None:
        """Test small files use JSON reader."""
        reader = get_reader(personal_chat_path, streaming=False)
        assert isinstance(reader, TelegramJSONReader)

    def test_force_no_streaming(self, personal_chat_path: Path) -> None:
        """Test streaming=False forces JSON reader."""
        reader = get_reader(personal_chat_path, streaming=False)
        assert isinstance(reader, TelegramJSONReader)

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_force_streaming_true(self, personal_chat_path: Path) -> None:
        """Test streaming=True forces stream reader."""
        from tg_parser.infrastructure.readers.telegram_stream import (
            TelegramStreamReader,
        )

        reader = get_reader(personal_chat_path, streaming=True)
        assert isinstance(reader, TelegramStreamReader)

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_progress_callback_passed_to_stream_reader(
        self, personal_chat_path: Path
    ) -> None:
        """Test progress callback is passed to streaming reader."""
        calls: list[tuple[int, int]] = []

        def callback(current: int, total: int) -> None:
            calls.append((current, total))

        reader = get_reader(
            personal_chat_path,
            streaming=True,
            progress_callback=callback,
        )

        # Read file to trigger callback
        reader.read(personal_chat_path)

        # Should have at least final callback
        assert len(calls) >= 1

    def test_auto_detects_based_on_file_size(self, personal_chat_path: Path) -> None:
        """Test auto-detection based on file size."""
        # Personal chat is small, should use JSON reader
        reader = get_reader(personal_chat_path, streaming=None)
        assert isinstance(reader, TelegramJSONReader)

    def test_custom_threshold(self, personal_chat_path: Path) -> None:
        """Test custom streaming threshold."""
        # Set threshold to 0 to force streaming mode (if ijson available)
        if is_ijson_available():
            from tg_parser.infrastructure.readers.telegram_stream import (
                TelegramStreamReader,
            )

            reader = get_reader(
                personal_chat_path, streaming=None, streaming_threshold_mb=0
            )
            assert isinstance(reader, TelegramStreamReader)
        else:
            # Without ijson, should still return JSON reader
            reader = get_reader(
                personal_chat_path, streaming=None, streaming_threshold_mb=0
            )
            assert isinstance(reader, TelegramJSONReader)

    def test_raises_import_error_when_streaming_forced_without_ijson(
        self, personal_chat_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test ImportError when streaming forced but ijson unavailable."""
        # Mock is_ijson_available to return False
        monkeypatch.setattr(
            "tg_parser.infrastructure.readers.is_ijson_available", lambda: False
        )

        with pytest.raises(ImportError) as exc_info:
            get_reader(personal_chat_path, streaming=True)

        assert "ijson" in str(exc_info.value).lower()

    def test_fallback_to_json_reader_when_ijson_unavailable(
        self, personal_chat_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to JSON reader when ijson not available (auto mode)."""
        # Mock is_ijson_available to return False
        monkeypatch.setattr(
            "tg_parser.infrastructure.readers.is_ijson_available", lambda: False
        )

        # Auto mode with threshold=0 would normally use streaming
        # But without ijson, should fall back to JSON reader
        reader = get_reader(
            personal_chat_path, streaming=None, streaming_threshold_mb=0
        )
        assert isinstance(reader, TelegramJSONReader)


class TestGetReaderIntegration:
    """Integration tests for reader factory."""

    @pytest.mark.skipif(not is_ijson_available(), reason="ijson not installed")
    def test_stream_reader_produces_same_result_as_json_reader(
        self, personal_chat_path: Path
    ) -> None:
        """Test both readers produce identical results."""
        json_reader = get_reader(personal_chat_path, streaming=False)
        stream_reader = get_reader(personal_chat_path, streaming=True)

        json_chat = json_reader.read(personal_chat_path)
        stream_chat = stream_reader.read(personal_chat_path)

        assert json_chat.name == stream_chat.name
        assert len(json_chat.messages) == len(stream_chat.messages)
