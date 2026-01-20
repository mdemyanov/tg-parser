"""Unit tests for CSVWriter."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from io import StringIO
from pathlib import Path

import pytest

from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.message import (
    Attachment,
    Message,
    MessageType,
    ReplyInfo,
)
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId
from tg_parser.infrastructure.writers.csv_writer import CSVWriter


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
                text="Hello @bob!",
                mentions=("@bob",),
            ),
            Message(
                id=MessageId(2),
                timestamp=datetime(2025, 1, 15, 10, 35),
                author_name="Bob",
                author_id=UserId("user222"),
                text="Hi there!",
                reply_to=ReplyInfo(
                    message_id=MessageId(1),
                    author="Alice",
                    preview="Hello @bob!",
                ),
                reactions={"👍": 3, "❤️": 1},
            ),
            Message(
                id=MessageId(3),
                timestamp=datetime(2025, 1, 16, 9, 0),
                author_name="Alice",
                author_id=UserId("user111"),
                text="Check this file",
                attachments=(Attachment(type="document", file_name="report.pdf"),),
            ),
        ],
        participants={
            UserId("user111"): Participant(
                id=UserId("user111"),
                name="Alice",
                username="alice",
                message_count=2,
            ),
            UserId("user222"): Participant(
                id=UserId("user222"),
                name="Bob",
                username="bob",
                message_count=1,
            ),
        },
        topics={},
    )


@pytest.fixture
def sample_chat_with_topics() -> Chat:
    """Create a sample chat with topics for testing."""
    return Chat(
        id=789012,
        name="Forum Chat",
        chat_type=ChatType.SUPERGROUP_FORUM,
        messages=[
            Message(
                id=MessageId(1),
                timestamp=datetime(2025, 1, 15, 10, 0),
                author_name="Alice",
                author_id=UserId("user111"),
                text="General discussion",
                topic_id=TopicId(1),
            ),
            Message(
                id=MessageId(2),
                timestamp=datetime(2025, 1, 15, 11, 0),
                author_name="Bob",
                author_id=UserId("user222"),
                text="Dev topic message",
                topic_id=TopicId(2),
            ),
        ],
        participants={},
        topics={},
    )


class TestCSVWriter:
    """Tests for CSVWriter class."""

    def test_header_row(self, sample_chat: Chat) -> None:
        """Test that header row contains expected columns."""
        writer = CSVWriter()
        result = writer.format_to_string(sample_chat)

        reader = csv.reader(StringIO(result))
        header = next(reader)

        assert "id" in header
        assert "timestamp" in header
        assert "author_id" in header
        assert "author_name" in header
        assert "text" in header
        assert "message_type" in header
        assert "topic_id" in header
        assert "reply_to_id" in header
        assert "forward_from" in header
        assert "mentions" in header
        assert "reactions" in header
        assert "attachments" in header

    def test_no_header_option(self, sample_chat: Chat) -> None:
        """Test output without header row."""
        writer = CSVWriter(include_header=False)
        result = writer.format_to_string(sample_chat)

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        # Should have 3 rows (one per message, no header)
        assert len(rows) == 3
        # First row should be data, not header
        assert rows[0][0] == "1"  # Message ID

    def test_basic_message_data(self, sample_chat: Chat) -> None:
        """Test that basic message data is correctly formatted."""
        writer = CSVWriter()
        result = writer.format_to_string(sample_chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        assert len(rows) == 3

        # First message
        msg1 = rows[0]
        assert msg1["id"] == "1"
        assert "2025-01-15" in msg1["timestamp"]
        assert msg1["author_id"] == "user111"
        assert msg1["author_name"] == "Alice"
        assert msg1["text"] == "Hello @bob!"
        assert msg1["message_type"] == "text"

    def test_mentions_as_json(self, sample_chat: Chat) -> None:
        """Test that mentions are formatted as JSON array."""
        writer = CSVWriter()
        result = writer.format_to_string(sample_chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        # First message has mentions
        msg1 = rows[0]
        mentions = json.loads(msg1["mentions"])
        assert "@bob" in mentions

        # Second message has no mentions
        msg2 = rows[1]
        assert msg2["mentions"] == ""

    def test_reactions_as_json(self, sample_chat: Chat) -> None:
        """Test that reactions are formatted as JSON object."""
        writer = CSVWriter()
        result = writer.format_to_string(sample_chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        # Second message has reactions
        msg2 = rows[1]
        reactions = json.loads(msg2["reactions"])
        assert reactions["👍"] == 3
        assert reactions["❤️"] == 1

        # First message has no reactions
        msg1 = rows[0]
        assert msg1["reactions"] == ""

    def test_attachments_as_json(self, sample_chat: Chat) -> None:
        """Test that attachments are formatted as JSON array."""
        writer = CSVWriter()
        result = writer.format_to_string(sample_chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        # Third message has attachments
        msg3 = rows[2]
        attachments = json.loads(msg3["attachments"])
        assert len(attachments) == 1
        assert attachments[0]["type"] == "document"
        assert attachments[0]["file_name"] == "report.pdf"

        # First message has no attachments
        msg1 = rows[0]
        assert msg1["attachments"] == ""

    def test_reply_to_id(self, sample_chat: Chat) -> None:
        """Test that reply_to_id is correctly formatted."""
        writer = CSVWriter()
        result = writer.format_to_string(sample_chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        # Second message has reply_to
        msg2 = rows[1]
        assert msg2["reply_to_id"] == "1"

        # First message has no reply_to
        msg1 = rows[0]
        assert msg1["reply_to_id"] == ""

    def test_topic_id(self, sample_chat_with_topics: Chat) -> None:
        """Test that topic_id is correctly formatted."""
        writer = CSVWriter()
        result = writer.format_to_string(sample_chat_with_topics)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        assert rows[0]["topic_id"] == "1"
        assert rows[1]["topic_id"] == "2"

    def test_write_to_file(self, sample_chat: Chat, tmp_path: Path) -> None:
        """Test writing to file."""
        writer = CSVWriter()
        output_file = tmp_path / "output.csv"
        writer.write(sample_chat, output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        reader = csv.DictReader(StringIO(content))
        rows = list(reader)
        assert len(rows) == 3
        assert rows[0]["author_name"] == "Alice"

    def test_write_messages_subset(self, sample_chat: Chat, tmp_path: Path) -> None:
        """Test writing messages subset."""
        writer = CSVWriter()
        output_file = tmp_path / "messages.csv"
        writer.write_messages(sample_chat.messages[:2], output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")

        reader = csv.DictReader(StringIO(content))
        rows = list(reader)
        assert len(rows) == 2

    def test_special_characters_escaped(self) -> None:
        """Test that special characters are properly escaped."""
        chat = Chat(
            id=1,
            name="Test",
            chat_type=ChatType.PERSONAL,
            messages=[
                Message(
                    id=MessageId(1),
                    timestamp=datetime(2025, 1, 15, 10, 0),
                    author_name="User",
                    author_id=UserId("user1"),
                    text='Text with "quotes", commas, and\nnewlines',
                ),
            ],
            participants={},
            topics={},
        )

        writer = CSVWriter()
        result = writer.format_to_string(chat)

        # Parse it back to ensure valid CSV
        reader = csv.DictReader(StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert "quotes" in rows[0]["text"]
        assert "commas" in rows[0]["text"]

    def test_unicode_content(self) -> None:
        """Test that Unicode content is properly handled."""
        chat = Chat(
            id=1,
            name="Test",
            chat_type=ChatType.PERSONAL,
            messages=[
                Message(
                    id=MessageId(1),
                    timestamp=datetime(2025, 1, 15, 10, 0),
                    author_name="Пользователь",
                    author_id=UserId("user1"),
                    text="Привет! 你好! 🎉",
                ),
            ],
            participants={},
            topics={},
        )

        writer = CSVWriter()
        result = writer.format_to_string(chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)
        assert rows[0]["author_name"] == "Пользователь"
        assert "Привет" in rows[0]["text"]
        assert "你好" in rows[0]["text"]
        assert "🎉" in rows[0]["text"]

    def test_empty_chat(self) -> None:
        """Test formatting empty chat."""
        chat = Chat(
            id=1,
            name="Empty Chat",
            chat_type=ChatType.PERSONAL,
            messages=[],
            participants={},
            topics={},
        )

        writer = CSVWriter()
        result = writer.format_to_string(chat)

        reader = csv.reader(StringIO(result))
        rows = list(reader)

        # Should have header only
        assert len(rows) == 1
        assert "id" in rows[0]

    def test_empty_chat_no_header(self) -> None:
        """Test formatting empty chat without header."""
        chat = Chat(
            id=1,
            name="Empty Chat",
            chat_type=ChatType.PERSONAL,
            messages=[],
            participants={},
            topics={},
        )

        writer = CSVWriter(include_header=False)
        result = writer.format_to_string(chat)

        # Should be empty
        assert result.strip() == ""

    def test_custom_delimiter(self, sample_chat: Chat) -> None:
        """Test using custom delimiter."""
        writer = CSVWriter(delimiter=";")
        result = writer.format_to_string(sample_chat)

        # Should use semicolons
        reader = csv.reader(StringIO(result), delimiter=";")
        rows = list(reader)
        assert len(rows) == 4  # header + 3 messages

    def test_forward_from_field(self) -> None:
        """Test that forward_from is correctly formatted."""
        chat = Chat(
            id=1,
            name="Test",
            chat_type=ChatType.PERSONAL,
            messages=[
                Message(
                    id=MessageId(1),
                    timestamp=datetime(2025, 1, 15, 10, 0),
                    author_name="User",
                    author_id=UserId("user1"),
                    text="Forwarded content",
                    forward_from="Original Author",
                ),
                Message(
                    id=MessageId(2),
                    timestamp=datetime(2025, 1, 15, 10, 5),
                    author_name="User",
                    author_id=UserId("user1"),
                    text="Normal message",
                ),
            ],
            participants={},
            topics={},
        )

        writer = CSVWriter()
        result = writer.format_to_string(chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        assert rows[0]["forward_from"] == "Original Author"
        assert rows[1]["forward_from"] == ""

    def test_service_message_type(self) -> None:
        """Test that service messages have correct type."""
        chat = Chat(
            id=1,
            name="Test",
            chat_type=ChatType.PERSONAL,
            messages=[
                Message(
                    id=MessageId(1),
                    timestamp=datetime(2025, 1, 15, 10, 0),
                    author_name="System",
                    author_id=UserId("system"),
                    text="User joined",
                    message_type=MessageType.SERVICE,
                ),
            ],
            participants={},
            topics={},
        )

        writer = CSVWriter()
        result = writer.format_to_string(chat)

        reader = csv.DictReader(StringIO(result))
        rows = list(reader)

        assert rows[0]["message_type"] == "service"
