"""Topic filter for messages."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.entities.topic import Topic
    from tg_parser.domain.value_objects.identifiers import TopicId


class TopicFilter:
    """Filter messages by topic title.

    Supports partial matching and case-insensitive comparison.
    Requires a topics_map to resolve topic_id to topic title.
    """

    def __init__(
        self,
        topics_map: dict[TopicId, Topic],
        include_topics: frozenset[str] | None = None,
        exclude_topics: frozenset[str] | None = None,
    ) -> None:
        """Initialize topic filter.

        Args:
            topics_map: Map of topic_id to Topic entity for title resolution.
            include_topics: Topic titles to include (partial match, case-insensitive).
            exclude_topics: Topic titles to exclude (partial match, case-insensitive).
        """
        self._topics_map = topics_map
        # Normalize to lowercase for case-insensitive matching
        self._include_topics = (
            frozenset(t.lower() for t in include_topics) if include_topics else None
        )
        self._exclude_topics = (
            frozenset(t.lower() for t in exclude_topics) if exclude_topics else None
        )

    def _get_topic_title(self, topic_id: TopicId | None) -> str | None:
        """Get topic title from topic_id.

        Args:
            topic_id: Topic ID to look up.

        Returns:
            Topic title or None if not found.
        """
        if topic_id is None:
            return None
        topic = self._topics_map.get(topic_id)
        return topic.title if topic else None

    def matches(self, message: Message) -> bool:
        """Check if message matches topic criteria.

        Logic:
        - Check exclusions first (if topic title matches any exclude pattern -> False)
        - If include_topics is specified and message has no topic -> False
        - If no inclusions specified -> True (after exclusions)
        - If inclusions specified -> True only if topic title matches any pattern

        Args:
            message: Message to check.

        Returns:
            True if message passes the topic filter.
        """
        topic_title = self._get_topic_title(message.topic_id)
        topic_title_lower = topic_title.lower() if topic_title else None

        # Check exclusions first
        if self._exclude_topics and topic_title_lower:
            for exclude in self._exclude_topics:
                if exclude in topic_title_lower:
                    return False

        # If include_topics is specified but message has no topic -> reject
        if self._include_topics and topic_title_lower is None:
            return False

        # If no inclusions specified, message passes (after exclusions)
        if not self._include_topics:
            return True

        # Check topic title matches any inclusion pattern
        if topic_title_lower:
            for include in self._include_topics:
                if include in topic_title_lower:
                    return True

        return False

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        """Filter messages by topic.

        Args:
            messages: Iterable of messages to filter.

        Yields:
            Messages that pass the topic filter.
        """
        for msg in messages:
            if self.matches(msg):
                yield msg
