"""Topic-based chunker for forum groups."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.value_objects.identifiers import TopicId


class TopicChunker:
    """Chunk messages by forum topic.

    Groups messages by their topic_id. Messages without a topic
    are grouped into a separate chunk. Chunks are ordered by
    the timestamp of their first message.
    """

    def chunk(
        self,
        messages: list[Message],
        max_tokens: int,  # noqa: ARG002
        **options: Any,
    ) -> list[list[Message]]:
        """Split messages into chunks by topic.

        Args:
            messages: Messages to chunk.
            max_tokens: Ignored for pure topic chunking (kept for protocol).
            **options: Optional "include_no_topic" (default True).

        Returns:
            List of message chunks, one per topic.
        """
        if not messages:
            return []

        include_no_topic = options.get("include_no_topic", True)

        # Group by topic_id
        by_topic: dict[TopicId | None, list[Message]] = defaultdict(list)
        for msg in messages:
            by_topic[msg.topic_id].append(msg)

        chunks: list[list[Message]] = []

        # Process topics in order of first message timestamp
        topic_order = sorted(
            by_topic.keys(),
            key=lambda tid: min(m.timestamp for m in by_topic[tid]),
        )

        for topic_id in topic_order:
            topic_messages = by_topic[topic_id]

            # Skip messages without topic if requested
            if topic_id is None and not include_no_topic:
                continue

            # Sort messages within topic by timestamp
            topic_messages.sort(key=lambda m: m.timestamp)
            chunks.append(topic_messages)

        return chunks

    def get_topic_ids(self, chunks: list[list[Message]]) -> list[TopicId | None]:
        """Get topic IDs for each chunk.

        Helper method to retrieve topic IDs after chunking.

        Args:
            chunks: List of message chunks from chunk() method.

        Returns:
            List of topic IDs corresponding to each chunk.
        """
        return [chunk[0].topic_id if chunk else None for chunk in chunks]
