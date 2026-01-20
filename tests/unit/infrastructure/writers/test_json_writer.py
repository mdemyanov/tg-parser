"""Unit tests for JSONWriter."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.message import (
    Attachment,
    Message,
    ReplyInfo,
)
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId
from tg_parser.infrastructure.writers.json_writer import JSONWriter


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
        participants={
            UserId("user111"): Participant(
                id=UserId("user111"),
                name="Alice",
                message_count=1,
            ),
            UserId("user222"): Participant(
                id=UserId("user222"),
                name="Bob",
                message_count=1,
            ),
        },
        topics={
            TopicId(1): Topic(
                id=TopicId(1),
                title="General",
                is_general=True,
            ),
            TopicId(2): Topic(
                id=TopicId(2),
                title="Development",
                created_at=datetime(2025, 1, 10, 12, 0),
            ),
        },
    )


class TestJSONWriter:
    """Tests for JSONWriter class."""

    def test_meta_section(self, sample_chat: Chat) -> None:
        """Test that meta section contains all required fields."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        assert "meta" in data
        meta = data["meta"]
        assert meta["chat_name"] == "Test Chat"
        assert meta["chat_type"] == "supergroup"
        assert "exported_at" in meta
        assert meta["message_count"] == 3
        assert "estimated_tokens" in meta
        assert meta["estimated_tokens"] > 0

    def test_date_range_in_meta(self, sample_chat: Chat) -> None:
        """Test that date range is correctly computed."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        date_range = data["meta"]["date_range"]
        assert date_range is not None
        assert "2025-01-15" in date_range["start"]
        assert "2025-01-16" in date_range["end"]

    def test_participants_section(self, sample_chat: Chat) -> None:
        """Test that participants are correctly formatted and sorted."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        assert "participants" in data
        participants = data["participants"]
        assert len(participants) == 2

        # Should be sorted by message count (Alice has 2, Bob has 1)
        assert participants[0]["name"] == "Alice"
        assert participants[0]["id"] == "user111"
        assert participants[0]["username"] == "alice"
        assert participants[0]["message_count"] == 2

        assert participants[1]["name"] == "Bob"
        assert participants[1]["message_count"] == 1

    def test_topics_section(self, sample_chat_with_topics: Chat) -> None:
        """Test that topics are correctly formatted."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat_with_topics)
        data = json.loads(result)

        assert "topics" in data
        topics = data["topics"]
        assert len(topics) == 2

        # Find General topic
        general = next(t for t in topics if t["title"] == "General")
        assert general["is_general"] is True
        assert general["created_at"] is None

        # Find Development topic
        dev = next(t for t in topics if t["title"] == "Development")
        assert dev["is_general"] is False
        assert dev["created_at"] is not None

    def test_messages_section(self, sample_chat: Chat) -> None:
        """Test that messages are correctly formatted."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        assert "messages" in data
        messages = data["messages"]
        assert len(messages) == 3

        msg1 = messages[0]
        assert msg1["id"] == 1
        assert "2025-01-15" in msg1["timestamp"]
        assert msg1["author_id"] == "user111"
        assert msg1["author_name"] == "Alice"
        assert msg1["text"] == "Hello @bob!"
        assert msg1["message_type"] == "text"
        assert "@bob" in msg1["mentions"]

    def test_reply_to_formatting(self, sample_chat: Chat) -> None:
        """Test that reply_to is correctly formatted."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        # Second message has reply_to
        msg2 = data["messages"][1]
        assert msg2["reply_to"] is not None
        assert msg2["reply_to"]["message_id"] == 1
        assert msg2["reply_to"]["author"] == "Alice"
        assert msg2["reply_to"]["preview"] == "Hello @bob!"

        # First message has no reply_to
        msg1 = data["messages"][0]
        assert msg1["reply_to"] is None

    def test_reactions_formatting(self, sample_chat: Chat) -> None:
        """Test that reactions are correctly formatted."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        # Second message has reactions
        msg2 = data["messages"][1]
        assert msg2["reactions"] == {"👍": 3, "❤️": 1}

        # First message has no reactions
        msg1 = data["messages"][0]
        assert msg1["reactions"] == {}

    def test_attachments_formatting(self, sample_chat: Chat) -> None:
        """Test that attachments are correctly formatted."""
        writer = JSONWriter()
        result = writer.format_to_string(sample_chat)
        data = json.loads(result)

        # Third message has attachments
        msg3 = data["messages"][2]
        assert len(msg3["attachments"]) == 1
        att = msg3["attachments"][0]
        assert att["type"] == "document"
        assert att["file_name"] == "report.pdf"

        # First message has no attachments
        msg1 = data["messages"][0]
        assert msg1["attachments"] == []

    def test_write_to_file(self, sample_chat: Chat, tmp_path: Path) -> None:
        """Test writing to file."""
        writer = JSONWriter()
        output_file = tmp_path / "output.json"
        writer.write(sample_chat, output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["meta"]["chat_name"] == "Test Chat"

    def test_write_messages_subset(self, sample_chat: Chat, tmp_path: Path) -> None:
        """Test writing messages subset with metadata."""
        writer = JSONWriter()
        output_file = tmp_path / "messages.json"
        writer.write_messages(
            sample_chat.messages[:2],
            output_file,
            metadata={"chat_name": "Test Chat", "topic": "General"},
        )

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        data = json.loads(content)
        assert data["meta"]["message_count"] == 2
        assert data["meta"]["chat_name"] == "Test Chat"
        assert data["meta"]["topic"] == "General"
        assert len(data["messages"]) == 2

    def test_compact_output(self, sample_chat: Chat) -> None:
        """Test compact output with indent=0."""
        writer = JSONWriter(indent=0)
        result = writer.format_to_string(sample_chat)

        # Should not have indentation
        assert "\n  " not in result
        # Should still be valid JSON
        data = json.loads(result)
        assert data["meta"]["chat_name"] == "Test Chat"

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

        writer = JSONWriter()
        result = writer.format_to_string(chat)
        data = json.loads(result)

        assert data["meta"]["message_count"] == 0
        assert data["meta"]["date_range"] is None
        assert data["participants"] == []
        assert data["topics"] == []
        assert data["messages"] == []
