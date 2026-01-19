"""Tests for TelegramJSONReader."""

from __future__ import annotations

from pathlib import Path

import pytest

from tg_parser.domain.entities.chat import ChatType
from tg_parser.domain.exceptions import InvalidExportError
from tg_parser.infrastructure.readers.telegram_json import TelegramJSONReader


class TestTelegramJSONReader:
    """Test TelegramJSONReader."""

    def test_read_personal_chat(self, personal_chat_path: Path) -> None:
        """Test reading personal chat export."""
        reader = TelegramJSONReader()
        chat = reader.read(personal_chat_path)

        assert chat.name == "Test User"
        assert chat.chat_type == ChatType.PERSONAL
        # 4 regular messages + 1 service = 5 total (reader doesn't filter)
        assert len(chat.messages) == 5

    def test_read_supergroup_with_topics(self, supergroup_with_topics_path: Path) -> None:
        """Test reading supergroup with topics."""
        reader = TelegramJSONReader()
        chat = reader.read(supergroup_with_topics_path)

        assert chat.name == "Test Group"
        assert chat.chat_type == ChatType.SUPERGROUP_FORUM
        # 2 explicitly created + 1 General = 3 topics
        assert len(chat.topics) >= 2

        # Check topic names
        topic_titles = {t.title for t in chat.topics.values()}
        assert "General" in topic_titles
        assert "Finances" in topic_titles

    def test_read_formatted_text(self, personal_chat_path: Path) -> None:
        """Test reading message with formatted text array."""
        reader = TelegramJSONReader()
        chat = reader.read(personal_chat_path)

        # Message 3 has formatted text
        msg3 = next(m for m in chat.messages if m.id == 3)
        assert "important" in msg3.text
        assert "Check this" in msg3.text

    def test_read_reply(self, personal_chat_path: Path) -> None:
        """Test reading message with reply."""
        reader = TelegramJSONReader()
        chat = reader.read(personal_chat_path)

        msg4 = next(m for m in chat.messages if m.id == 4)
        assert msg4.reply_to is not None
        assert msg4.reply_to.message_id == 3

    def test_read_reactions(self, supergroup_with_topics_path: Path) -> None:
        """Test reading message with reactions."""
        reader = TelegramJSONReader()
        chat = reader.read(supergroup_with_topics_path)

        msg6 = next(m for m in chat.messages if m.id == 6)
        assert "👍" in msg6.reactions
        assert msg6.reactions["👍"] == 3

    def test_participants_extracted(self, supergroup_with_topics_path: Path) -> None:
        """Test that participants are extracted."""
        reader = TelegramJSONReader()
        chat = reader.read(supergroup_with_topics_path)

        names = {p.name for p in chat.participants.values()}
        assert "Admin" in names
        assert "User1" in names
        assert "User2" in names
        assert "User3" in names

    def test_invalid_file_raises_error(self, tmp_path: Path) -> None:
        """Test that invalid JSON raises error."""
        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not json")

        reader = TelegramJSONReader()
        with pytest.raises(InvalidExportError):
            reader.read(invalid_file)

    def test_missing_required_fields_raises_error(self, tmp_path: Path) -> None:
        """Test that missing required fields raises error."""
        invalid_file = tmp_path / "incomplete.json"
        invalid_file.write_text('{"name": "Test"}')  # missing type and messages

        reader = TelegramJSONReader()
        with pytest.raises(InvalidExportError):
            reader.read(invalid_file)


class TestTextNormalization:
    """Test text normalization from various formats."""

    def test_simple_string(self, tmp_path: Path) -> None:
        """Test normalizing simple string text."""
        file_path = tmp_path / "test.json"
        file_path.write_text('''{
            "name": "Test",
            "type": "personal_chat",
            "id": 1,
            "messages": [
                {"id": 1, "type": "message", "date": "2024-01-01T00:00:00",
                 "from": "User", "from_id": "user1", "text": "Simple text"}
            ]
        }''')

        reader = TelegramJSONReader()
        chat = reader.read(file_path)
        assert chat.messages[0].text == "Simple text"

    def test_array_with_formatting(self, tmp_path: Path) -> None:
        """Test normalizing text array with formatting objects."""
        file_path = tmp_path / "test.json"
        file_path.write_text('''{
            "name": "Test",
            "type": "personal_chat",
            "id": 1,
            "messages": [
                {"id": 1, "type": "message", "date": "2024-01-01T00:00:00",
                 "from": "User", "from_id": "user1",
                 "text": ["Normal ", {"type": "bold", "text": "bold"}, " text"]}
            ]
        }''')

        reader = TelegramJSONReader()
        chat = reader.read(file_path)
        assert chat.messages[0].text == "Normal bold text"

    def test_empty_text(self, tmp_path: Path) -> None:
        """Test normalizing empty text."""
        file_path = tmp_path / "test.json"
        file_path.write_text('''{
            "name": "Test",
            "type": "personal_chat",
            "id": 1,
            "messages": [
                {"id": 1, "type": "message", "date": "2024-01-01T00:00:00",
                 "from": "User", "from_id": "user1", "text": ""}
            ]
        }''')

        reader = TelegramJSONReader()
        chat = reader.read(file_path)
        assert chat.messages[0].text == ""
