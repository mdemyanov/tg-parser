"""Tests for topic filter."""

from __future__ import annotations

from datetime import datetime

import pytest

from tg_parser.domain.entities.message import Message, MessageType
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId
from tg_parser.infrastructure.filters.topic_filter import TopicFilter


def make_message(
    *,
    topic_id: TopicId | None = None,
    text: str = "Test message",
) -> Message:
    """Create a test message."""
    return Message(
        id=MessageId(1),
        timestamp=datetime(2024, 1, 15, 10, 0),
        author_name="Alice",
        author_id=UserId("user1"),
        text=text,
        message_type=MessageType.TEXT,
        topic_id=topic_id,
    )


@pytest.fixture
def topics_map() -> dict[TopicId, Topic]:
    """Sample topics map."""
    return {
        TopicId(1): Topic(id=TopicId(1), title="General", is_general=True),
        TopicId(2): Topic(id=TopicId(2), title="Finances Q4"),
        TopicId(3): Topic(id=TopicId(3), title="Technical Discussion"),
    }


class TestTopicFilter:
    """Test TopicFilter."""

    def test_include_topic_matches(self, topics_map: dict[TopicId, Topic]) -> None:
        """Test including specific topics."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"Finances"}),
        )
        assert filter_.matches(make_message(topic_id=TopicId(2))) is True
        assert filter_.matches(make_message(topic_id=TopicId(1))) is False

    def test_include_topic_partial_match(
        self, topics_map: dict[TopicId, Topic]
    ) -> None:
        """Test partial match for topic inclusion."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"Q4"}),
        )
        # "Finances Q4" matches "Q4"
        assert filter_.matches(make_message(topic_id=TopicId(2))) is True

    def test_include_topic_case_insensitive(
        self, topics_map: dict[TopicId, Topic]
    ) -> None:
        """Test case-insensitive matching."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"GENERAL"}),
        )
        assert filter_.matches(make_message(topic_id=TopicId(1))) is True

    def test_exclude_topic_matches(self, topics_map: dict[TopicId, Topic]) -> None:
        """Test excluding specific topics."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            exclude_topics=frozenset({"General"}),
        )
        assert filter_.matches(make_message(topic_id=TopicId(1))) is False
        assert filter_.matches(make_message(topic_id=TopicId(2))) is True

    def test_exclude_topic_partial_match(
        self, topics_map: dict[TopicId, Topic]
    ) -> None:
        """Test partial match for topic exclusion."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            exclude_topics=frozenset({"Technical"}),
        )
        assert filter_.matches(make_message(topic_id=TopicId(3))) is False

    def test_include_and_exclude(self, topics_map: dict[TopicId, Topic]) -> None:
        """Test both include and exclude - exclude takes priority."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"Finances", "General"}),
            exclude_topics=frozenset({"General"}),
        )
        assert filter_.matches(make_message(topic_id=TopicId(2))) is True
        assert filter_.matches(make_message(topic_id=TopicId(1))) is False  # Excluded

    def test_no_topic_with_include_filter(
        self, topics_map: dict[TopicId, Topic]
    ) -> None:
        """Test message without topic_id when include is specified."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"Finances"}),
        )
        assert filter_.matches(make_message(topic_id=None)) is False

    def test_no_topic_with_exclude_filter_only(
        self, topics_map: dict[TopicId, Topic]
    ) -> None:
        """Test message without topic_id with only exclude filter."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            exclude_topics=frozenset({"General"}),
        )
        # No inclusion filter, message has no topic, should pass
        assert filter_.matches(make_message(topic_id=None)) is True

    def test_empty_filter_passes_all(self, topics_map: dict[TopicId, Topic]) -> None:
        """Test empty filter passes all messages."""
        filter_ = TopicFilter(topics_map=topics_map)
        assert filter_.matches(make_message(topic_id=TopicId(1))) is True
        assert filter_.matches(make_message(topic_id=TopicId(2))) is True
        assert filter_.matches(make_message(topic_id=None)) is True

    def test_unknown_topic_id(self, topics_map: dict[TopicId, Topic]) -> None:
        """Test message with topic_id not in topics_map."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"Finances"}),
        )
        # Unknown topic_id -> topic_title is None -> rejected
        assert filter_.matches(make_message(topic_id=TopicId(999))) is False

    def test_unknown_topic_id_exclude_only(
        self, topics_map: dict[TopicId, Topic]
    ) -> None:
        """Test message with unknown topic_id and only exclude filter."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            exclude_topics=frozenset({"General"}),
        )
        # Unknown topic_id -> topic_title is None
        # passes (no exclude match, no include specified)
        assert filter_.matches(make_message(topic_id=TopicId(999))) is True

    def test_filter_iterator(self, topics_map: dict[TopicId, Topic]) -> None:
        """Test filter() returns iterator."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"Finances"}),
        )
        messages = [
            make_message(topic_id=TopicId(1)),
            make_message(topic_id=TopicId(2)),
            make_message(topic_id=TopicId(3)),
        ]
        result = list(filter_.filter(messages))
        assert len(result) == 1
        assert result[0].topic_id == TopicId(2)

    def test_multiple_include_topics(self, topics_map: dict[TopicId, Topic]) -> None:
        """Test with multiple include topic patterns."""
        filter_ = TopicFilter(
            topics_map=topics_map,
            include_topics=frozenset({"General", "Technical"}),
        )
        assert filter_.matches(make_message(topic_id=TopicId(1))) is True  # General
        assert filter_.matches(make_message(topic_id=TopicId(2))) is False  # Finances
        assert filter_.matches(make_message(topic_id=TopicId(3))) is True  # Technical

    def test_empty_topics_map(self) -> None:
        """Test with empty topics map."""
        filter_ = TopicFilter(
            topics_map={},
            include_topics=frozenset({"Finances"}),
        )
        # No topics can match -> all rejected when include is set
        assert filter_.matches(make_message(topic_id=TopicId(1))) is False
        assert filter_.matches(make_message(topic_id=None)) is False

    def test_empty_topics_map_exclude_only(self) -> None:
        """Test with empty topics map and only exclude filter."""
        filter_ = TopicFilter(
            topics_map={},
            exclude_topics=frozenset({"General"}),
        )
        # Nothing to exclude since no titles can be resolved
        assert filter_.matches(make_message(topic_id=TopicId(1))) is True
        assert filter_.matches(make_message(topic_id=None)) is True
