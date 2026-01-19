"""Tests for extraction guide in writers."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.message import Message
from tg_parser.domain.value_objects.identifiers import MessageId, UserId
from tg_parser.infrastructure.writers.json_writer import JSONWriter
from tg_parser.infrastructure.writers.kb_template import KBTemplateWriter
from tg_parser.infrastructure.writers.markdown import MarkdownWriter


@pytest.fixture
def sample_chat() -> Chat:
    """Create a sample chat for testing."""
    return Chat(
        id=123456,
        name="Test Chat",
        chat_type=ChatType.SUPERGROUP,
        messages=[
            Message(
                id=MessageId(1),
                timestamp=datetime(2025, 1, 15, 10, 30),
                author_name="Alice",
                author_id=UserId("user111"),
                text="Hello!",
            ),
        ],
        participants={},
        topics={},
    )


class TestMarkdownWriterExtractionGuide:
    """Test extraction guide in MarkdownWriter."""

    def test_guide_not_included_by_default(self, sample_chat: Chat) -> None:
        """Test guide is not included when flag is False."""
        writer = MarkdownWriter()
        result = writer.format_to_string(sample_chat)

        assert "Инструкция по извлечению артефактов" not in result

    def test_guide_included_when_flag_true(self, sample_chat: Chat) -> None:
        """Test guide is appended when flag is True."""
        writer = MarkdownWriter(include_extraction_guide=True)
        result = writer.format_to_string(sample_chat)

        assert "Инструкция по извлечению артефактов" in result
        assert "Решения" in result
        assert "Договорённости" in result
        assert "Задачи и Action Items" in result
        assert "Блокеры" in result

    def test_guide_at_end_of_output(self, sample_chat: Chat) -> None:
        """Test that guide is at the end of output."""
        writer = MarkdownWriter(include_extraction_guide=True)
        result = writer.format_to_string(sample_chat)

        # Guide should be after the messages
        messages_end = result.find("Hello!")
        guide_start = result.find("Инструкция по извлечению артефактов")
        assert guide_start > messages_end


class TestKBTemplateWriterExtractionGuide:
    """Test extraction guide in KBTemplateWriter."""

    def test_guide_not_included_by_default(self, sample_chat: Chat) -> None:
        """Test guide is not included when flag is False."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        assert "Инструкция по извлечению артефактов" not in result

    def test_guide_included_when_flag_true(self, sample_chat: Chat) -> None:
        """Test guide is appended when flag is True."""
        writer = KBTemplateWriter(include_extraction_guide=True)
        result = writer.format_to_string(sample_chat)

        assert "Инструкция по извлечению артефактов" in result
        assert "Решения" in result


class TestJSONWriterExtractionGuide:
    """Test extraction guide in JSONWriter."""

    def test_guide_not_included_by_default(self, sample_chat: Chat) -> None:
        """Test guide is not included when flag is False."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        assert "extraction_guide" not in data["meta"]

    def test_guide_in_metadata_when_flag_true(self, sample_chat: Chat) -> None:
        """Test guide is added to meta.extraction_guide field."""
        writer = JSONWriter(include_extraction_guide=True)
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        assert "extraction_guide" in data["meta"]
        assert "Инструкция" in data["meta"]["extraction_guide"]
        assert "Решения" in data["meta"]["extraction_guide"]
