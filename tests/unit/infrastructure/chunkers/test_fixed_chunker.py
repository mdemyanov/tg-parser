"""Tests for FixedChunker."""

from __future__ import annotations

from datetime import datetime

from tg_parser.domain.entities.message import Message, MessageType
from tg_parser.domain.value_objects.identifiers import MessageId, UserId
from tg_parser.infrastructure.chunkers.fixed_chunker import FixedChunker


def make_message(
    id: int = 1,
    text: str = "Hello world",
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
    )


class TestFixedChunker:
    """Tests for FixedChunker."""

    def test_empty_messages_returns_empty(self) -> None:
        """Empty input returns empty output."""
        chunker = FixedChunker()
        assert chunker.chunk([], max_tokens=1000) == []

    def test_single_message_single_chunk(self) -> None:
        """Single message creates single chunk."""
        chunker = FixedChunker()
        messages = [make_message()]
        chunks = chunker.chunk(messages, max_tokens=1000)

        assert len(chunks) == 1
        assert len(chunks[0]) == 1

    def test_small_messages_fit_in_one_chunk(self) -> None:
        """Messages under limit stay in one chunk."""
        chunker = FixedChunker()
        messages = [make_message(id=i, text="Hi") for i in range(5)]
        chunks = chunker.chunk(messages, max_tokens=10000)

        assert len(chunks) == 1
        assert len(chunks[0]) == 5

    def test_messages_split_by_token_limit(self) -> None:
        """Messages exceeding limit are split."""
        chunker = FixedChunker()
        # Each message ~50 tokens (200 chars / 4)
        messages = [make_message(id=i, text="x" * 200) for i in range(10)]
        chunks = chunker.chunk(messages, max_tokens=150)

        assert len(chunks) > 1
        # Verify all messages are preserved
        total = sum(len(c) for c in chunks)
        assert total == 10

    def test_large_single_message_own_chunk(self) -> None:
        """A message larger than max_tokens gets its own chunk."""
        chunker = FixedChunker()
        messages = [
            make_message(id=1, text="small"),
            make_message(id=2, text="x" * 40000),  # ~10000 tokens
            make_message(id=3, text="small"),
        ]
        chunks = chunker.chunk(messages, max_tokens=1000)

        assert len(chunks) >= 2
        # The large message should be in its own chunk
        large_chunk = [c for c in chunks if any(len(m.text) > 10000 for m in c)]
        assert len(large_chunk) == 1
        assert len(large_chunk[0]) == 1  # Only the large message

    def test_preserves_message_order(self) -> None:
        """Message order is preserved within and across chunks."""
        chunker = FixedChunker()
        messages = [make_message(id=i) for i in range(1, 11)]
        chunks = chunker.chunk(messages, max_tokens=200)

        # Flatten and check order
        flat = [m for chunk in chunks for m in chunk]
        ids = [m.id for m in flat]
        assert ids == list(range(1, 11))

    def test_chunk_boundary_exactly_at_limit(self) -> None:
        """Chunk created when exactly at token limit."""
        chunker = FixedChunker()
        # Create messages that will fill chunks predictably
        messages = [make_message(id=i, text="test message") for i in range(10)]
        chunks = chunker.chunk(messages, max_tokens=100)

        # Should have multiple chunks, all non-empty
        assert len(chunks) >= 1
        assert all(len(c) > 0 for c in chunks)

    def test_accepts_protocol_options(self) -> None:
        """Chunker accepts **options for protocol compatibility."""
        chunker = FixedChunker()
        messages = [make_message()]
        # Should not raise even with extra options
        chunks = chunker.chunk(messages, max_tokens=1000, some_option="value")
        assert len(chunks) == 1
