"""Unit tests for KBTemplateWriter."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.message import Attachment, Message, ReplyInfo
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId
from tg_parser.infrastructure.writers.kb_template import KBTemplateWriter

_ = TYPE_CHECKING  # Avoid unused import


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
                author_name="Алексей Иванов",
                author_id=UserId("user111"),
                text="Привет @bob! Как дела?",
                mentions=("@bob",),
            ),
            Message(
                id=MessageId(2),
                timestamp=datetime(2025, 1, 15, 10, 35),
                author_name="Bob Smith",
                author_id=UserId("user222"),
                text="Hi there!",
                reply_to=ReplyInfo(
                    message_id=MessageId(1),
                    author="Алексей Иванов",
                    preview="Привет @bob! Как дела?",
                ),
                reactions={"👍": 3},
            ),
            Message(
                id=MessageId(3),
                timestamp=datetime(2025, 1, 16, 9, 0),
                author_name="Алексей Иванов",
                author_id=UserId("user111"),
                text="Посмотри файл",
                attachments=(
                    Attachment(type="document", file_name="report.pdf"),
                ),
            ),
        ],
        participants={
            UserId("user111"): Participant(
                id=UserId("user111"),
                name="Алексей Иванов",
                username="aivanov",
                message_count=2,
            ),
            UserId("user222"): Participant(
                id=UserId("user222"),
                name="Bob Smith",
                username="bob",
                message_count=1,
            ),
        },
        topics={},
    )


@pytest.fixture
def sample_chat_single_topic() -> Chat:
    """Create a sample chat where all messages belong to one topic."""
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
                text="Discussion about finances",
                topic_id=TopicId(2),
            ),
            Message(
                id=MessageId(2),
                timestamp=datetime(2025, 1, 15, 11, 0),
                author_name="Bob",
                author_id=UserId("user222"),
                text="Budget review",
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
                title="Finances",
            ),
        },
    )


class TestKBTemplateWriter:
    """Tests for KBTemplateWriter class."""

    def test_yaml_frontmatter_fields(self, sample_chat: Chat) -> None:
        """Test that YAML frontmatter contains all required fields."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Check frontmatter delimiters
        assert result.startswith("---\n")
        assert "\n---\n" in result

        # Extract frontmatter
        frontmatter = result.split("---")[1]

        assert "title:" in frontmatter
        assert "Test Chat" in frontmatter
        assert "date:" in frontmatter
        assert "chat_type: supergroup" in frontmatter
        assert "participants:" in frontmatter
        assert "date_range:" in frontmatter
        assert "message_count: 3" in frontmatter
        assert "estimated_tokens:" in frontmatter
        assert "tags:" in frontmatter
        assert "telegram-export" in frontmatter

    def test_wikilinks_format_in_frontmatter(self, sample_chat: Chat) -> None:
        """Test that participants in frontmatter use WikiLinks format."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Check WikiLinks in participants section
        assert "[[user111|Алексей Иванов]]" in result
        assert "[[user222|Bob Smith]]" in result

    def test_wikilinks_in_message_headers(self, sample_chat: Chat) -> None:
        """Test that message headers contain WikiLinks."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Check WikiLinks in H3 headers
        assert "### 10:30 — [[user111|Алексей Иванов]]" in result
        assert "### 10:35 — [[user222|Bob Smith]]" in result
        assert "### 09:00 — [[user111|Алексей Иванов]]" in result

    def test_preserves_mentions(self, sample_chat: Chat) -> None:
        """Test that @mentions are preserved as-is in message body."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # @bob should remain as @bob, not converted to WikiLink
        assert "@bob" in result
        # The @bob mention should NOT be in WikiLinks format in body
        lines = result.split("\n")
        for line in lines:
            if "@bob" in line and not line.startswith("###"):
                # In message body, @bob should be plain text
                assert "[[" not in line or "user" in line

    def test_date_range_formatting(self, sample_chat: Chat) -> None:
        """Test date range is formatted correctly."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Should have date range in frontmatter
        assert "2025-01-15 — 2025-01-16" in result

    def test_single_topic_in_frontmatter(self, sample_chat_single_topic: Chat) -> None:
        """Test that topic field appears when all messages are in one topic."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat_single_topic)

        # Should have topic field in frontmatter
        frontmatter = result.split("---")[1]
        assert "topic: Finances" in frontmatter

    def test_no_topic_with_multiple_topics(self, sample_chat: Chat) -> None:
        """Test that topic field does not appear with multiple topics."""
        # Add topic to one message
        sample_chat.messages[0] = Message(
            id=MessageId(1),
            timestamp=sample_chat.messages[0].timestamp,
            author_name=sample_chat.messages[0].author_name,
            author_id=sample_chat.messages[0].author_id,
            text=sample_chat.messages[0].text,
            topic_id=TopicId(1),
        )
        sample_chat.messages[1] = Message(
            id=MessageId(2),
            timestamp=sample_chat.messages[1].timestamp,
            author_name=sample_chat.messages[1].author_name,
            author_id=sample_chat.messages[1].author_id,
            text=sample_chat.messages[1].text,
            topic_id=TopicId(2),
        )
        sample_chat.topics = {
            TopicId(1): Topic(id=TopicId(1), title="General"),
            TopicId(2): Topic(id=TopicId(2), title="Dev"),
        }

        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Should NOT have topic field in frontmatter
        frontmatter = result.split("---")[1]
        assert "topic:" not in frontmatter

    def test_estimated_tokens_calculation(self, sample_chat: Chat) -> None:
        """Test that estimated tokens are calculated."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Extract estimated_tokens value
        match = re.search(r"estimated_tokens: (\d+)", result)
        assert match is not None
        tokens = int(match.group(1))
        assert tokens > 0

    def test_messages_grouped_by_date(self, sample_chat: Chat) -> None:
        """Test that messages are grouped by date with H2 headers."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        assert "## 2025-01-15" in result
        assert "## 2025-01-16" in result

    def test_reply_formatting(self, sample_chat: Chat) -> None:
        """Test that replies are formatted with quote blocks."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Reply preview should be in quote block
        assert "> Привет @bob! Как дела?" in result

    def test_attachments_formatting(self, sample_chat: Chat) -> None:
        """Test that attachments are included."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        assert "[Attachment: document - report.pdf]" in result

    def test_reactions_formatting(self, sample_chat: Chat) -> None:
        """Test that reactions are included."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        assert "*Reactions: 👍 3*" in result

    def test_write_to_file(self, sample_chat: Chat, tmp_path: Path) -> None:
        """Test writing to file."""
        writer = KBTemplateWriter()
        output_file = tmp_path / "output.md"
        writer.write(sample_chat, output_file)

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "---" in content
        assert "Test Chat" in content

    def test_write_messages_subset(self, sample_chat: Chat, tmp_path: Path) -> None:
        """Test writing messages subset with metadata."""
        writer = KBTemplateWriter()
        output_file = tmp_path / "messages.md"
        writer.write_messages(
            sample_chat.messages[:2],
            output_file,
            metadata={"chat_name": "Test Chat", "topic": "General"},
        )

        assert output_file.exists()
        content = output_file.read_text(encoding="utf-8")
        assert "---" in content
        assert "message_count: 2" in content

    def test_cyrillic_in_wikilinks(self, sample_chat: Chat) -> None:
        """Test that Cyrillic names work in WikiLinks."""
        writer = KBTemplateWriter()
        result = writer.format_to_string(sample_chat)

        # Cyrillic should be preserved as-is
        assert "[[user111|Алексей Иванов]]" in result

    def test_no_reactions_when_disabled(self, sample_chat: Chat) -> None:
        """Test that reactions are not included when disabled."""
        writer = KBTemplateWriter(include_reactions=False)
        result = writer.format_to_string(sample_chat)

        assert "*Reactions:" not in result

    def test_no_attachments_when_disabled(self, sample_chat: Chat) -> None:
        """Test that attachments are not included when disabled."""
        writer = KBTemplateWriter(include_attachments=False)
        result = writer.format_to_string(sample_chat)

        assert "[Attachment:" not in result

    def test_custom_timestamp_format(self, sample_chat: Chat) -> None:
        """Test custom timestamp format."""
        writer = KBTemplateWriter(timestamp_format="%H:%M:%S")
        result = writer.format_to_string(sample_chat)

        assert "### 10:30:00 —" in result

    def test_custom_date_format(self, sample_chat: Chat) -> None:
        """Test custom date format."""
        writer = KBTemplateWriter(date_format="%d.%m.%Y")
        result = writer.format_to_string(sample_chat)

        assert "## 15.01.2025" in result

    def test_forward_info(self) -> None:
        """Test that forward info is included."""
        chat = Chat(
            id=1,
            name="Test",
            chat_type=ChatType.PERSONAL,
            messages=[
                Message(
                    id=MessageId(1),
                    timestamp=datetime(2025, 1, 15, 10, 0),
                    author_name="Alice",
                    author_id=UserId("user111"),
                    text="Forwarded content",
                    forward_from="News Channel",
                ),
            ],
            participants={
                UserId("user111"): Participant(
                    id=UserId("user111"),
                    name="Alice",
                    message_count=1,
                ),
            },
            topics={},
        )

        writer = KBTemplateWriter()
        result = writer.format_to_string(chat)

        assert "*Forwarded from News Channel*" in result
