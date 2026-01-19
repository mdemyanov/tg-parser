"""Get chat statistics use case."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tg_parser.domain.entities.chat import Chat


@dataclass
class ChatStatistics:
    """Aggregated chat statistics."""

    chat_name: str
    chat_type: str
    total_messages: int
    participants_count: int
    topics_count: int
    date_range: tuple[datetime, datetime] | None
    top_senders: list[tuple[str, int]]
    messages_by_topic: dict[str, int]
    estimated_tokens: int


class GetStatisticsUseCase:
    """Use case for computing chat statistics."""

    def execute(
        self,
        chat: Chat,
        top_senders_count: int = 10,
    ) -> ChatStatistics:
        """Compute statistics for a chat.

        Args:
            chat: Chat entity to analyze.
            top_senders_count: Number of top senders to include.

        Returns:
            ChatStatistics with aggregated data.
        """
        from tg_parser.infrastructure.token_counters.simple_counter import (
            SimpleTokenCounter,
        )

        # Count messages by sender
        sender_counts: Counter[str] = Counter()
        for msg in chat.messages:
            sender_counts[msg.author_name] += 1

        top_senders = sender_counts.most_common(top_senders_count)

        # Count messages by topic
        messages_by_topic: dict[str, int] = {}
        for topic_id, topic in chat.topics.items():
            count = len(chat.messages_by_topic(topic_id))
            messages_by_topic[topic.title] = count

        # Estimate tokens
        counter = SimpleTokenCounter()
        estimated_tokens = counter.count_messages(chat.messages)

        return ChatStatistics(
            chat_name=chat.name,
            chat_type=chat.chat_type.value,
            total_messages=len(chat.messages),
            participants_count=len(chat.participants),
            topics_count=len(chat.topics),
            date_range=chat.date_range,
            top_senders=top_senders,
            messages_by_topic=messages_by_topic,
            estimated_tokens=estimated_tokens,
        )
