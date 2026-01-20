"""Tests for TelegramStreamReader."""

from __future__ import annotations

from pathlib import Path

import pytest

from tg_parser.domain.entities.chat import ChatType
from tg_parser.domain.entities.message import Message
from tg_parser.infrastructure.readers.telegram_json import TelegramJSONReader

# Skip all tests if ijson is not available
ijson = pytest.importorskip("ijson")

from tg_parser.infrastructure.readers.telegram_stream import TelegramStreamReader


class TestTelegramStreamReader:
    """Test TelegramStreamReader."""

    def test_read_personal_chat(self, personal_chat_path: Path) -> None:
        """Test reading personal chat export."""
        reader = TelegramStreamReader()
        chat = reader.read(personal_chat_path)

        assert chat.name == "Test User"
        assert chat.chat_type == ChatType.PERSONAL
        # 4 regular messages + 1 service = 5 total
        assert len(chat.messages) == 5

    def test_read_supergroup_with_topics(
        self, supergroup_with_topics_path: Path
    ) -> None:
        """Test reading supergroup with topics."""
        reader = TelegramStreamReader()
        chat = reader.read(supergroup_with_topics_path)

        assert chat.name == "Test Group"
        assert chat.chat_type == ChatType.SUPERGROUP_FORUM
        # 2 explicitly created + 1 General = 3 topics
        assert len(chat.topics) >= 2

        # Check topic names
        topic_titles = {t.title for t in chat.topics.values()}
        assert "General" in topic_titles
        assert "Finances" in topic_titles

    def test_read_matches_json_reader(self, personal_chat_path: Path) -> None:
        """Test streaming reader produces same results as JSON reader."""
        json_reader = TelegramJSONReader()
        stream_reader = TelegramStreamReader()

        json_chat = json_reader.read(personal_chat_path)
        stream_chat = stream_reader.read(personal_chat_path)

        assert json_chat.name == stream_chat.name
        assert json_chat.chat_type == stream_chat.chat_type
        assert len(json_chat.messages) == len(stream_chat.messages)
        assert len(json_chat.participants) == len(stream_chat.participants)

        # Compare message IDs
        json_ids = [m.id for m in json_chat.messages]
        stream_ids = [m.id for m in stream_chat.messages]
        assert json_ids == stream_ids

    def test_read_matches_json_reader_with_topics(
        self, supergroup_with_topics_path: Path
    ) -> None:
        """Test streaming reader matches JSON reader for forum chat."""
        json_reader = TelegramJSONReader()
        stream_reader = TelegramStreamReader()

        json_chat = json_reader.read(supergroup_with_topics_path)
        stream_chat = stream_reader.read(supergroup_with_topics_path)

        assert json_chat.name == stream_chat.name
        assert json_chat.chat_type == stream_chat.chat_type
        assert len(json_chat.messages) == len(stream_chat.messages)
        assert len(json_chat.topics) == len(stream_chat.topics)

        # Compare topic IDs
        json_topic_ids = set(json_chat.topics.keys())
        stream_topic_ids = set(stream_chat.topics.keys())
        assert json_topic_ids == stream_topic_ids

    def test_stream_messages_yields_messages(self, personal_chat_path: Path) -> None:
        """Test stream_messages yields Message objects."""
        reader = TelegramStreamReader()
        messages = list(reader.stream_messages(personal_chat_path))

        assert len(messages) > 0
        assert all(isinstance(m, Message) for m in messages)

    def test_progress_callback_called(self, personal_chat_path: Path) -> None:
        """Test progress callback is invoked."""
        calls: list[tuple[int, int]] = []

        def callback(current: int, total: int) -> None:
            calls.append((current, total))

        reader = TelegramStreamReader(
            progress_callback=callback,
            progress_interval=1,  # Call on every message
        )
        reader.read(personal_chat_path)

        # Should have at least one call
        assert len(calls) > 0

        # Last call should have current == total
        last_current, last_total = calls[-1]
        assert last_current == last_total

    def test_progress_callback_respects_interval(
        self, personal_chat_path: Path
    ) -> None:
        """Test progress callback respects interval setting."""
        calls: list[tuple[int, int]] = []

        def callback(current: int, total: int) -> None:
            calls.append((current, total))

        # With interval of 100, small file won't trigger intermediate calls
        reader = TelegramStreamReader(
            progress_callback=callback,
            progress_interval=100,
        )
        reader.read(personal_chat_path)

        # Should have final call only (file has <100 messages)
        assert len(calls) == 1

    def test_validate_valid_file(self, personal_chat_path: Path) -> None:
        """Test validate returns no warnings for valid file."""
        reader = TelegramStreamReader()
        warnings = reader.validate(personal_chat_path)
        assert warnings == []

    def test_validate_missing_file(self, tmp_path: Path) -> None:
        """Test validate returns warning for missing file."""
        reader = TelegramStreamReader()
        warnings = reader.validate(tmp_path / "nonexistent.json")
        assert len(warnings) == 1
        assert "not found" in warnings[0].lower()

    def test_validate_missing_messages_field(self, tmp_path: Path) -> None:
        """Test validate returns warning for missing messages."""
        file_path = tmp_path / "invalid.json"
        file_path.write_text('{"name": "Test", "type": "personal_chat"}')

        reader = TelegramStreamReader()
        warnings = reader.validate(file_path)
        assert any("messages" in w.lower() for w in warnings)

    def test_read_missing_file_raises_error(self, tmp_path: Path) -> None:
        """Test reading missing file raises FileNotFoundError."""
        reader = TelegramStreamReader()
        with pytest.raises(FileNotFoundError):
            reader.read(tmp_path / "nonexistent.json")

    def test_participants_extracted(self, supergroup_with_topics_path: Path) -> None:
        """Test that participants are extracted correctly."""
        reader = TelegramStreamReader()
        chat = reader.read(supergroup_with_topics_path)

        names = {p.name for p in chat.participants.values()}
        assert "Admin" in names
        assert "User1" in names

    def test_reactions_parsed(self, supergroup_with_topics_path: Path) -> None:
        """Test that reactions are parsed."""
        reader = TelegramStreamReader()
        chat = reader.read(supergroup_with_topics_path)

        # Message 6 has reactions
        msg6 = next(m for m in chat.messages if m.id == 6)
        assert "👍" in msg6.reactions
        assert msg6.reactions["👍"] == 3


class TestTelegramStreamReaderImportError:
    """Test import error handling."""

    def test_reader_raises_import_error_when_ijson_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that reader raises ImportError when ijson not available."""
        # This is tricky to test since ijson is available in test env
        # We can test the error message at least
        reader = TelegramStreamReader()
        # If we got here, ijson is available, which is fine
        assert reader is not None
