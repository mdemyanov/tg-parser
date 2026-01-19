"""Tests for message filters."""

from __future__ import annotations

import re
from datetime import datetime

from tg_parser.domain.entities.message import Message, MessageType
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.value_objects.date_range import DateRange
from tg_parser.domain.value_objects.filter_spec import FilterSpecification
from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId
from tg_parser.infrastructure.filters.composite import CompositeFilter, build_filter
from tg_parser.infrastructure.filters.date_filter import DateFilter
from tg_parser.infrastructure.filters.sender_filter import SenderFilter


def make_message(
    *,
    id: int = 1,
    timestamp: datetime = datetime(2024, 1, 15, 10, 0),
    author_name: str = "Alice",
    text: str = "Hello",
    message_type: MessageType = MessageType.TEXT,
    forward_from: str | None = None,
    topic_id: TopicId | None = None,
) -> Message:
    """Create a test message."""
    return Message(
        id=MessageId(id),
        timestamp=timestamp,
        author_name=author_name,
        author_id=UserId("user1"),
        text=text,
        message_type=message_type,
        forward_from=forward_from,
        topic_id=topic_id,
    )


class TestDateFilter:
    """Test DateFilter."""

    def test_filter_within_range(self) -> None:
        """Test message within date range passes."""
        date_range = DateRange(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
        )
        filter_ = DateFilter(date_range)
        msg = make_message(timestamp=datetime(2024, 1, 15, 10, 0))
        assert filter_.matches(msg) is True

    def test_filter_before_range(self) -> None:
        """Test message before range fails."""
        date_range = DateRange(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
        )
        filter_ = DateFilter(date_range)
        msg = make_message(timestamp=datetime(2023, 12, 15, 10, 0))
        assert filter_.matches(msg) is False

    def test_filter_after_range(self) -> None:
        """Test message after range fails."""
        date_range = DateRange(
            start=datetime(2024, 1, 1),
            end=datetime(2024, 1, 31),
        )
        filter_ = DateFilter(date_range)
        msg = make_message(timestamp=datetime(2024, 2, 15, 10, 0))
        assert filter_.matches(msg) is False

    def test_filter_start_only(self) -> None:
        """Test filter with start date only."""
        date_range = DateRange(start=datetime(2024, 1, 1))
        filter_ = DateFilter(date_range)

        assert filter_.matches(make_message(timestamp=datetime(2024, 1, 15))) is True
        assert filter_.matches(make_message(timestamp=datetime(2023, 12, 15))) is False


class TestSenderFilter:
    """Test SenderFilter."""

    def test_include_sender(self) -> None:
        """Test including specific senders."""
        filter_ = SenderFilter(
            include_names=frozenset({"Alice", "Bob"}),
        )
        assert filter_.matches(make_message(author_name="Alice")) is True
        assert filter_.matches(make_message(author_name="Bob")) is True
        assert filter_.matches(make_message(author_name="Charlie")) is False

    def test_exclude_sender(self) -> None:
        """Test excluding specific senders."""
        filter_ = SenderFilter(
            exclude_names=frozenset({"Bot"}),
        )
        assert filter_.matches(make_message(author_name="Alice")) is True
        assert filter_.matches(make_message(author_name="Bot")) is False

    def test_include_and_exclude(self) -> None:
        """Test both include and exclude."""
        filter_ = SenderFilter(
            include_names=frozenset({"Alice", "Bot"}),
            exclude_names=frozenset({"Bot"}),
        )
        # Exclude takes priority
        assert filter_.matches(make_message(author_name="Alice")) is True
        assert filter_.matches(make_message(author_name="Bot")) is False

    def test_case_insensitive(self) -> None:
        """Test case-insensitive matching."""
        filter_ = SenderFilter(include_names=frozenset({"alice"}))
        assert filter_.matches(make_message(author_name="Alice")) is True
        assert filter_.matches(make_message(author_name="ALICE")) is True


class TestCompositeFilter:
    """Test CompositeFilter."""

    def test_all_filters_must_match(self) -> None:
        """Test AND logic for composite filter."""
        filter_ = CompositeFilter(
            filters=[
                SenderFilter(include_names=frozenset({"Alice"})),
                DateFilter(DateRange(start=datetime(2024, 1, 1))),
            ]
        )
        # Both conditions met
        assert filter_.matches(make_message(author_name="Alice", timestamp=datetime(2024, 1, 15))) is True
        # Only sender matches
        assert filter_.matches(make_message(author_name="Alice", timestamp=datetime(2023, 1, 15))) is False
        # Only date matches
        assert filter_.matches(make_message(author_name="Bob", timestamp=datetime(2024, 1, 15))) is False

    def test_empty_filter_passes_all(self) -> None:
        """Test empty composite filter passes all messages."""
        filter_ = CompositeFilter(filters=[])
        assert filter_.matches(make_message()) is True


class TestBuildFilter:
    """Test build_filter function."""

    def test_build_from_spec(self) -> None:
        """Test building filter from specification."""
        spec = FilterSpecification(
            date_range=DateRange(start=datetime(2024, 1, 1)),
            senders=frozenset({"Alice"}),
            exclude_service=True,
        )
        filter_ = build_filter(spec)

        # Matches all criteria
        msg1 = make_message(
            timestamp=datetime(2024, 1, 15),
            author_name="Alice",
            message_type=MessageType.TEXT,
        )
        assert filter_.matches(msg1) is True

        # Fails date
        msg2 = make_message(
            timestamp=datetime(2023, 1, 15),
            author_name="Alice",
        )
        assert filter_.matches(msg2) is False

        # Fails sender
        msg3 = make_message(
            timestamp=datetime(2024, 1, 15),
            author_name="Bob",
        )
        assert filter_.matches(msg3) is False

    def test_build_empty_spec(self) -> None:
        """Test building filter from empty spec."""
        spec = FilterSpecification()
        filter_ = build_filter(spec)
        # Only service filter is added by default
        assert filter_.matches(make_message(message_type=MessageType.TEXT)) is True

    def test_service_filter(self) -> None:
        """Test service message filtering."""
        spec = FilterSpecification(exclude_service=True)
        filter_ = build_filter(spec)

        assert filter_.matches(make_message(message_type=MessageType.TEXT)) is True
        assert filter_.matches(make_message(message_type=MessageType.SERVICE)) is False

    def test_forward_filter(self) -> None:
        """Test forward message filtering."""
        spec = FilterSpecification(exclude_forwards=True)
        filter_ = build_filter(spec)

        assert filter_.matches(make_message(forward_from=None)) is True
        assert filter_.matches(make_message(forward_from="Someone")) is False

    def test_content_filter(self) -> None:
        """Test content pattern filtering."""
        spec = FilterSpecification(
            content_pattern=re.compile(r"hello", re.IGNORECASE),
            exclude_service=False,
        )
        filter_ = build_filter(spec)

        assert filter_.matches(make_message(text="Hello world")) is True
        assert filter_.matches(make_message(text="HELLO")) is True
        assert filter_.matches(make_message(text="Goodbye")) is False


class TestBuildFilterWithTopics:
    """Test build_filter with topic filtering."""

    def test_build_with_topics_filter(self) -> None:
        """Test building filter with topics."""
        topics_map = {
            TopicId(1): Topic(id=TopicId(1), title="General"),
            TopicId(2): Topic(id=TopicId(2), title="Finances"),
        }
        spec = FilterSpecification(
            topics=frozenset({"Finances"}),
            exclude_service=False,
        )
        filter_ = build_filter(spec, topics_map=topics_map)

        msg1 = make_message(topic_id=TopicId(2))
        msg2 = make_message(topic_id=TopicId(1))

        assert filter_.matches(msg1) is True
        assert filter_.matches(msg2) is False

    def test_build_with_exclude_topics(self) -> None:
        """Test building filter with exclude topics."""
        topics_map = {
            TopicId(1): Topic(id=TopicId(1), title="General"),
            TopicId(2): Topic(id=TopicId(2), title="Finances"),
        }
        spec = FilterSpecification(
            exclude_topics=frozenset({"General"}),
            exclude_service=False,
        )
        filter_ = build_filter(spec, topics_map=topics_map)

        msg1 = make_message(topic_id=TopicId(1))  # General
        msg2 = make_message(topic_id=TopicId(2))  # Finances

        assert filter_.matches(msg1) is False
        assert filter_.matches(msg2) is True

    def test_build_without_topics_map_ignores_filter(self) -> None:
        """Test topics filter is skipped when topics_map is None."""
        spec = FilterSpecification(
            topics=frozenset({"Finances"}),
            exclude_service=False,
        )
        filter_ = build_filter(spec)  # No topics_map

        # Filter should pass everything since TopicFilter wasn't added
        msg = make_message()
        assert filter_.matches(msg) is True

    def test_build_with_topics_and_other_filters(self) -> None:
        """Test combining topic filter with other filters."""
        topics_map = {
            TopicId(1): Topic(id=TopicId(1), title="General"),
            TopicId(2): Topic(id=TopicId(2), title="Finances"),
        }
        spec = FilterSpecification(
            topics=frozenset({"Finances"}),
            senders=frozenset({"Alice"}),
            exclude_service=False,
        )
        filter_ = build_filter(spec, topics_map=topics_map)

        # Matches both topic and sender
        msg1 = make_message(topic_id=TopicId(2), author_name="Alice")
        assert filter_.matches(msg1) is True

        # Wrong topic
        msg2 = make_message(topic_id=TopicId(1), author_name="Alice")
        assert filter_.matches(msg2) is False

        # Wrong sender
        msg3 = make_message(topic_id=TopicId(2), author_name="Bob")
        assert filter_.matches(msg3) is False
