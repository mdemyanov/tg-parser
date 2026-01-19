"""Composite filter combining multiple filters with AND logic."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

from tg_parser.infrastructure.filters.date_filter import DateFilter
from tg_parser.infrastructure.filters.sender_filter import SenderFilter
from tg_parser.infrastructure.filters.topic_filter import TopicFilter

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.entities.topic import Topic
    from tg_parser.domain.protocols.filter import FilterProtocol
    from tg_parser.domain.value_objects.filter_spec import FilterSpecification
    from tg_parser.domain.value_objects.identifiers import TopicId


class CompositeFilter:
    """Combines multiple filters with AND logic."""

    def __init__(self, filters: list[FilterProtocol]) -> None:
        """Initialize with list of filters.

        Args:
            filters: List of filters to combine.
        """
        self._filters = filters

    def matches(self, message: Message) -> bool:
        """Message must match ALL filters.

        Args:
            message: Message to check.

        Returns:
            True if message passes all filters.
        """
        return all(f.matches(message) for f in self._filters)

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        """Filter messages through all filters.

        Args:
            messages: Iterable of messages to filter.

        Yields:
            Messages that pass all filters.
        """
        for msg in messages:
            if self.matches(msg):
                yield msg


def build_filter(
    spec: FilterSpecification,
    topics_map: dict[TopicId, Topic] | None = None,
) -> CompositeFilter:
    """Build composite filter from specification.

    Args:
        spec: Filter specification with all criteria.
        topics_map: Optional map of topic_id to Topic for topic filtering.

    Returns:
        CompositeFilter combining all specified filters.
    """
    filters: list[FilterProtocol] = []

    # Date filter
    if spec.date_range and not spec.date_range.is_empty():
        filters.append(DateFilter(spec.date_range))

    # Sender filter
    if spec.senders or spec.sender_ids or spec.exclude_senders:
        filters.append(
            SenderFilter(
                include_names=spec.senders if spec.senders else None,
                include_ids=spec.sender_ids if spec.sender_ids else None,
                exclude_names=spec.exclude_senders if spec.exclude_senders else None,
            )
        )

    # Topic filter (requires topics_map)
    if (spec.topics or spec.exclude_topics) and topics_map is not None:
        filters.append(
            TopicFilter(
                topics_map=topics_map,
                include_topics=spec.topics if spec.topics else None,
                exclude_topics=spec.exclude_topics if spec.exclude_topics else None,
            )
        )

    # Service message filter
    if spec.exclude_service:
        filters.append(_ServiceFilter(exclude=True))

    # Empty message filter
    if spec.exclude_empty:
        filters.append(_EmptyFilter(exclude=True))

    # Forward filter
    if spec.exclude_forwards:
        filters.append(_ForwardFilter(exclude=True))

    # Content pattern filter
    if spec.content_pattern:
        filters.append(_ContentPatternFilter(spec.content_pattern))

    # Min length filter
    if spec.min_length > 0:
        filters.append(_MinLengthFilter(spec.min_length))

    # Attachment filter
    if spec.has_attachment is not None:
        filters.append(_AttachmentFilter(require=spec.has_attachment))

    # Reactions filter
    if spec.has_reactions is not None:
        filters.append(_ReactionsFilter(require=spec.has_reactions))

    return CompositeFilter(filters)


class _ServiceFilter:
    """Filter service messages."""

    def __init__(self, exclude: bool = True) -> None:
        self._exclude = exclude

    def matches(self, message: Message) -> bool:
        if self._exclude:
            return not message.is_service
        return message.is_service

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        for msg in messages:
            if self.matches(msg):
                yield msg


class _EmptyFilter:
    """Filter empty messages."""

    def __init__(self, exclude: bool = True) -> None:
        self._exclude = exclude

    def matches(self, message: Message) -> bool:
        if self._exclude:
            return message.has_text or message.has_attachments
        return not message.has_text

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        for msg in messages:
            if self.matches(msg):
                yield msg


class _ForwardFilter:
    """Filter forwarded messages."""

    def __init__(self, exclude: bool = True) -> None:
        self._exclude = exclude

    def matches(self, message: Message) -> bool:
        if self._exclude:
            return not message.is_forward
        return message.is_forward

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        for msg in messages:
            if self.matches(msg):
                yield msg


class _ContentPatternFilter:
    """Filter by content regex pattern."""

    def __init__(self, pattern: re.Pattern[str]) -> None:
        self._pattern = pattern

    def matches(self, message: Message) -> bool:
        return bool(self._pattern.search(message.text))

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        for msg in messages:
            if self.matches(msg):
                yield msg


class _MinLengthFilter:
    """Filter by minimum text length."""

    def __init__(self, min_length: int) -> None:
        self._min_length = min_length

    def matches(self, message: Message) -> bool:
        return len(message.text.strip()) >= self._min_length

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        for msg in messages:
            if self.matches(msg):
                yield msg


class _AttachmentFilter:
    """Filter by attachment presence."""

    def __init__(self, require: bool = True) -> None:
        self._require = require

    def matches(self, message: Message) -> bool:
        if self._require:
            return message.has_attachments
        return not message.has_attachments

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        for msg in messages:
            if self.matches(msg):
                yield msg


class _ReactionsFilter:
    """Filter by reactions presence."""

    def __init__(self, require: bool = True) -> None:
        self._require = require

    def matches(self, message: Message) -> bool:
        if self._require:
            return message.has_reactions
        return not message.has_reactions

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        for msg in messages:
            if self.matches(msg):
                yield msg
