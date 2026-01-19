"""Hybrid chunker: topic-first with time-window fallback."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tg_parser.infrastructure.token_counters.simple_counter import SimpleTokenCounter

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.value_objects.identifiers import TopicId


@dataclass
class HybridChunkInfo:
    """Internal info about a hybrid chunk.

    Attributes:
        messages: Messages in this chunk.
        topic_id: Topic ID (None if no topic).
        part_number: Part number within the topic (1-based).
        total_parts: Total number of parts for this topic.
    """

    messages: list[Message]
    topic_id: TopicId | None
    part_number: int
    total_parts: int


class HybridChunker:
    """Hybrid chunker: group by topic, split large topics by time.

    First groups messages by topic_id. If a topic exceeds max_tokens,
    it's split into multiple parts using token-based chunking while
    preserving chronological order.
    """

    def __init__(self, token_counter: SimpleTokenCounter | None = None) -> None:
        """Initialize with optional custom token counter.

        Args:
            token_counter: Token counter to use. If None, uses default.
        """
        self._counter = token_counter or SimpleTokenCounter()

    def chunk(
        self,
        messages: list[Message],
        max_tokens: int,
        **options: Any,
    ) -> list[list[Message]]:
        """Split messages using hybrid strategy.

        Args:
            messages: Messages to chunk.
            max_tokens: Maximum tokens per chunk.
            **options: Optional settings (unused).

        Returns:
            List of message chunks.
        """
        chunk_infos = self.chunk_with_info(messages, max_tokens, **options)
        return [info.messages for info in chunk_infos]

    def chunk_with_info(
        self,
        messages: list[Message],
        max_tokens: int,
        **options: Any,  # noqa: ARG002
    ) -> list[HybridChunkInfo]:
        """Split messages with detailed chunk info.

        Args:
            messages: Messages to chunk.
            max_tokens: Maximum tokens per chunk.
            **options: Optional settings (unused).

        Returns:
            List of HybridChunkInfo with messages and metadata.
        """
        if not messages:
            return []

        # Group by topic_id
        by_topic: dict[TopicId | None, list[Message]] = defaultdict(list)
        for msg in messages:
            by_topic[msg.topic_id].append(msg)

        result: list[HybridChunkInfo] = []

        # Process topics in chronological order (by first message)
        topic_order = sorted(
            by_topic.keys(),
            key=lambda tid: min(m.timestamp for m in by_topic[tid]),
        )

        for topic_id in topic_order:
            topic_messages = sorted(by_topic[topic_id], key=lambda m: m.timestamp)
            topic_tokens = self._counter.count_messages(topic_messages)

            if topic_tokens <= max_tokens:
                # Topic fits in one chunk
                result.append(
                    HybridChunkInfo(
                        messages=topic_messages,
                        topic_id=topic_id,
                        part_number=1,
                        total_parts=1,
                    )
                )
            else:
                # Split by tokens (time-ordered)
                parts = self._split_by_tokens(topic_messages, max_tokens)
                total_parts = len(parts)

                for i, part_messages in enumerate(parts, start=1):
                    result.append(
                        HybridChunkInfo(
                            messages=part_messages,
                            topic_id=topic_id,
                            part_number=i,
                            total_parts=total_parts,
                        )
                    )

        return result

    def _split_by_tokens(
        self,
        messages: list[Message],
        max_tokens: int,
    ) -> list[list[Message]]:
        """Split messages into parts by token limit.

        Args:
            messages: Messages to split (should be sorted by timestamp).
            max_tokens: Maximum tokens per part.

        Returns:
            List of message parts.
        """
        parts: list[list[Message]] = []
        current_part: list[Message] = []
        current_tokens = 0

        for msg in messages:
            msg_tokens = self._counter.count_messages([msg])

            if current_tokens + msg_tokens > max_tokens and current_part:
                parts.append(current_part)
                current_part = []
                current_tokens = 0

            current_part.append(msg)
            current_tokens += msg_tokens

        if current_part:
            parts.append(current_part)

        return parts
