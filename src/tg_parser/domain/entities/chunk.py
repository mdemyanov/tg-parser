"""Chunk entity for grouped messages ready for LLM processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.value_objects.identifiers import TopicId


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Metadata describing a chunk's origin and context.

    Attributes:
        chunk_index: Zero-based index of this chunk in the sequence.
        total_chunks: Total number of chunks in the sequence.
        topic_id: Topic ID if chunk is topic-specific (None for non-forum or mixed).
        topic_title: Human-readable topic title.
        part_number: Part number within a topic (for split topics), 1-based.
        total_parts: Total parts for this topic (1 if not split).
        date_range_start: Start timestamp of messages in this chunk.
        date_range_end: End timestamp of messages in this chunk.
        strategy: Chunking strategy used ("fixed", "topic", "hybrid").
        estimated_tokens: Estimated token count for this chunk.
    """

    chunk_index: int
    total_chunks: int
    topic_id: TopicId | None = None
    topic_title: str | None = None
    part_number: int = 1
    total_parts: int = 1
    date_range_start: datetime | None = None
    date_range_end: datetime | None = None
    strategy: str = "fixed"
    estimated_tokens: int = 0


@dataclass(frozen=True, slots=True)
class Chunk:
    """A chunk of messages ready for LLM processing.

    Immutable container for a subset of chat messages with
    associated metadata for context preservation.
    """

    messages: tuple[Message, ...]
    metadata: ChunkMetadata

    @property
    def message_count(self) -> int:
        """Number of messages in this chunk."""
        return len(self.messages)

    @property
    def is_topic_part(self) -> bool:
        """Check if this chunk is part of a split topic."""
        return self.metadata.total_parts > 1

    @property
    def has_topic(self) -> bool:
        """Check if this chunk is associated with a topic."""
        return self.metadata.topic_id is not None
