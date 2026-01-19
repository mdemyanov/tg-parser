"""Tests for TopicChunker."""

from __future__ import annotations

from datetime import datetime

from tg_parser.domain.entities.message import Message, MessageType
from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId
from tg_parser.infrastructure.chunkers.topic_chunker import TopicChunker


def make_message(
    id: int = 1,
    topic_id: int | None = None,
    timestamp: datetime | None = None,
) -> Message:
    """Create a test message."""
    return Message(
        id=MessageId(id),
        timestamp=timestamp or datetime(2024, 1, 15, 10, 0),
        author_name="Alice",
        author_id=UserId("user1"),
        text="Hello",
        message_type=MessageType.TEXT,
        topic_id=TopicId(topic_id) if topic_id else None,
    )


class TestTopicChunker:
    """Tests for TopicChunker."""

    def test_empty_messages_returns_empty(self) -> None:
        """Empty input returns empty output."""
        chunker = TopicChunker()
        assert chunker.chunk([], max_tokens=1000) == []

    def test_single_topic_single_chunk(self) -> None:
        """Messages from one topic go to one chunk."""
        chunker = TopicChunker()
        messages = [
            make_message(id=1, topic_id=10),
            make_message(id=2, topic_id=10),
            make_message(id=3, topic_id=10),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000)

        assert len(chunks) == 1
        assert len(chunks[0]) == 3

    def test_multiple_topics_multiple_chunks(self) -> None:
        """Messages from different topics go to different chunks."""
        chunker = TopicChunker()
        messages = [
            make_message(id=1, topic_id=10, timestamp=datetime(2024, 1, 15, 10, 0)),
            make_message(id=2, topic_id=20, timestamp=datetime(2024, 1, 15, 11, 0)),
            make_message(id=3, topic_id=10, timestamp=datetime(2024, 1, 15, 12, 0)),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000)

        assert len(chunks) == 2
        # Check topic grouping
        topic_ids = [c[0].topic_id for c in chunks]
        assert set(topic_ids) == {TopicId(10), TopicId(20)}

    def test_no_topic_messages_grouped(self) -> None:
        """Messages without topic_id are grouped together."""
        chunker = TopicChunker()
        messages = [
            make_message(id=1, topic_id=None),
            make_message(id=2, topic_id=10),
            make_message(id=3, topic_id=None),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000)

        assert len(chunks) == 2
        no_topic_chunk = [c for c in chunks if c[0].topic_id is None]
        assert len(no_topic_chunk) == 1
        assert len(no_topic_chunk[0]) == 2

    def test_topics_ordered_by_first_message(self) -> None:
        """Chunks are ordered by first message timestamp."""
        chunker = TopicChunker()
        messages = [
            make_message(id=1, topic_id=20, timestamp=datetime(2024, 1, 15, 12, 0)),
            make_message(id=2, topic_id=10, timestamp=datetime(2024, 1, 15, 10, 0)),
            make_message(id=3, topic_id=30, timestamp=datetime(2024, 1, 15, 11, 0)),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000)

        # Should be ordered: topic 10, topic 30, topic 20
        topic_order = [c[0].topic_id for c in chunks]
        assert topic_order == [TopicId(10), TopicId(30), TopicId(20)]

    def test_messages_within_topic_sorted(self) -> None:
        """Messages within a topic are sorted by timestamp."""
        chunker = TopicChunker()
        messages = [
            make_message(id=3, topic_id=10, timestamp=datetime(2024, 1, 15, 12, 0)),
            make_message(id=1, topic_id=10, timestamp=datetime(2024, 1, 15, 10, 0)),
            make_message(id=2, topic_id=10, timestamp=datetime(2024, 1, 15, 11, 0)),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000)

        ids = [m.id for m in chunks[0]]
        assert ids == [MessageId(1), MessageId(2), MessageId(3)]

    def test_exclude_no_topic_option(self) -> None:
        """Option to exclude messages without topic."""
        chunker = TopicChunker()
        messages = [
            make_message(id=1, topic_id=None),
            make_message(id=2, topic_id=10),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000, include_no_topic=False)

        assert len(chunks) == 1
        assert chunks[0][0].topic_id == TopicId(10)

    def test_get_topic_ids_helper(self) -> None:
        """get_topic_ids returns correct topic IDs."""
        chunker = TopicChunker()
        messages = [
            make_message(id=1, topic_id=10),
            make_message(id=2, topic_id=20),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000)
        topic_ids = chunker.get_topic_ids(chunks)

        assert set(topic_ids) == {TopicId(10), TopicId(20)}

    def test_get_topic_ids_empty_chunk(self) -> None:
        """get_topic_ids handles empty chunks gracefully."""
        chunker = TopicChunker()
        # Empty list case
        assert chunker.get_topic_ids([]) == []
        # List with empty chunk (edge case)
        assert chunker.get_topic_ids([[]]) == [None]
