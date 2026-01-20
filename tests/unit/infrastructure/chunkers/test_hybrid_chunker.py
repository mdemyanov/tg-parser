"""Tests for HybridChunker."""

from __future__ import annotations

from datetime import datetime

from tg_parser.domain.entities.message import Message, MessageType
from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId
from tg_parser.infrastructure.chunkers.hybrid_chunker import HybridChunker


def make_message(
    id: int = 1,
    topic_id: int | None = None,
    text: str = "Hello",
    timestamp: datetime | None = None,
) -> Message:
    """Create a test message."""
    return Message(
        id=MessageId(id),
        timestamp=timestamp or datetime(2024, 1, 15, 10, 0),
        author_name="Alice",
        author_id=UserId("user1"),
        text=text,
        message_type=MessageType.TEXT,
        topic_id=TopicId(topic_id) if topic_id else None,
    )


class TestHybridChunker:
    """Tests for HybridChunker."""

    def test_empty_messages_returns_empty(self) -> None:
        """Empty input returns empty output."""
        chunker = HybridChunker()
        assert chunker.chunk([], max_tokens=1000) == []
        assert chunker.chunk_with_info([], max_tokens=1000) == []

    def test_small_topic_stays_together(self) -> None:
        """A topic under token limit stays in one chunk."""
        chunker = HybridChunker()
        messages = [
            make_message(id=1, topic_id=10),
            make_message(id=2, topic_id=10),
        ]
        chunks = chunker.chunk(messages, max_tokens=10000)

        assert len(chunks) == 1
        assert len(chunks[0]) == 2

    def test_small_topic_metadata(self) -> None:
        """Small topic has correct metadata (part 1 of 1)."""
        chunker = HybridChunker()
        messages = [
            make_message(id=1, topic_id=10),
            make_message(id=2, topic_id=10),
        ]
        chunks_info = chunker.chunk_with_info(messages, max_tokens=10000)

        assert len(chunks_info) == 1
        assert chunks_info[0].topic_id == TopicId(10)
        assert chunks_info[0].part_number == 1
        assert chunks_info[0].total_parts == 1

    def test_large_topic_split_into_parts(self) -> None:
        """A topic exceeding token limit is split."""
        chunker = HybridChunker()
        # Each message ~50 tokens (200 chars / 4 + overhead)
        messages = [
            make_message(
                id=i,
                topic_id=10,
                text="x" * 200,
                timestamp=datetime(2024, 1, 15, 10, i),
            )
            for i in range(10)
        ]
        chunks_info = chunker.chunk_with_info(messages, max_tokens=150)

        assert len(chunks_info) > 1
        # All should have same topic_id
        assert all(info.topic_id == TopicId(10) for info in chunks_info)
        # Part numbers should be sequential
        parts = [info.part_number for info in chunks_info]
        assert parts == list(range(1, len(chunks_info) + 1))
        # Total parts should match
        assert all(info.total_parts == len(chunks_info) for info in chunks_info)

    def test_mixed_topics_with_split(self) -> None:
        """Multiple topics where one needs splitting."""
        chunker = HybridChunker()
        messages = [
            # Small topic
            make_message(
                id=1, topic_id=10, text="small", timestamp=datetime(2024, 1, 15, 9, 0)
            ),
            # Large topic
            make_message(
                id=2,
                topic_id=20,
                text="x" * 200,
                timestamp=datetime(2024, 1, 15, 10, 0),
            ),
            make_message(
                id=3,
                topic_id=20,
                text="x" * 200,
                timestamp=datetime(2024, 1, 15, 10, 1),
            ),
            make_message(
                id=4,
                topic_id=20,
                text="x" * 200,
                timestamp=datetime(2024, 1, 15, 10, 2),
            ),
        ]
        chunks_info = chunker.chunk_with_info(messages, max_tokens=150)

        # Topic 10 should have 1 part
        topic_10_chunks = [i for i in chunks_info if i.topic_id == TopicId(10)]
        assert len(topic_10_chunks) == 1
        assert topic_10_chunks[0].total_parts == 1

        # Topic 20 may have multiple parts depending on token calculation
        topic_20_chunks = [i for i in chunks_info if i.topic_id == TopicId(20)]
        assert len(topic_20_chunks) >= 1
        if len(topic_20_chunks) > 1:
            assert all(i.total_parts == len(topic_20_chunks) for i in topic_20_chunks)

    def test_preserves_time_order_within_split_topic(self) -> None:
        """Messages stay in timestamp order when topic is split."""
        chunker = HybridChunker()
        messages = [
            make_message(
                id=i,
                topic_id=10,
                text="x" * 200,
                timestamp=datetime(2024, 1, 15, 10, i),
            )
            for i in range(10)
        ]
        chunks_info = chunker.chunk_with_info(messages, max_tokens=150)

        # Flatten and check order
        all_ids = []
        for info in chunks_info:
            all_ids.extend(m.id for m in info.messages)

        expected = [MessageId(i) for i in range(10)]
        assert all_ids == expected

    def test_chunk_without_info_returns_messages_only(self) -> None:
        """chunk() method returns just message lists."""
        chunker = HybridChunker()
        messages = [make_message(id=i, topic_id=10) for i in range(3)]
        chunks = chunker.chunk(messages, max_tokens=10000)

        assert len(chunks) == 1
        assert isinstance(chunks[0], list)
        assert all(isinstance(m, Message) for m in chunks[0])

    def test_topics_ordered_by_first_message(self) -> None:
        """Topics are ordered by their first message timestamp."""
        chunker = HybridChunker()
        messages = [
            make_message(id=1, topic_id=20, timestamp=datetime(2024, 1, 15, 12, 0)),
            make_message(id=2, topic_id=10, timestamp=datetime(2024, 1, 15, 10, 0)),
            make_message(id=3, topic_id=30, timestamp=datetime(2024, 1, 15, 11, 0)),
        ]
        chunks_info = chunker.chunk_with_info(messages, max_tokens=10000)

        # Should be ordered: topic 10, topic 30, topic 20
        topic_order = [info.topic_id for info in chunks_info]
        assert topic_order == [TopicId(10), TopicId(30), TopicId(20)]

    def test_no_topic_messages_grouped(self) -> None:
        """Messages without topic are grouped together."""
        chunker = HybridChunker()
        messages = [
            make_message(id=1, topic_id=None, timestamp=datetime(2024, 1, 15, 10, 0)),
            make_message(id=2, topic_id=10, timestamp=datetime(2024, 1, 15, 11, 0)),
            make_message(id=3, topic_id=None, timestamp=datetime(2024, 1, 15, 12, 0)),
        ]
        chunks_info = chunker.chunk_with_info(messages, max_tokens=10000)

        no_topic_chunks = [i for i in chunks_info if i.topic_id is None]
        assert len(no_topic_chunks) == 1
        assert len(no_topic_chunks[0].messages) == 2

    def test_single_large_message_in_topic(self) -> None:
        """Single message larger than max_tokens gets its own part."""
        chunker = HybridChunker()
        messages = [
            make_message(id=1, topic_id=10, text="x" * 40000),  # Very large
        ]
        chunks_info = chunker.chunk_with_info(messages, max_tokens=1000)

        # Should be one chunk with the large message
        assert len(chunks_info) == 1
        assert len(chunks_info[0].messages) == 1
        assert chunks_info[0].part_number == 1
        assert chunks_info[0].total_parts == 1
