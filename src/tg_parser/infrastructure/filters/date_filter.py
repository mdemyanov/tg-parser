"""Date range filter for messages."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.value_objects.date_range import DateRange


class DateFilter:
    """Filter messages by date range."""

    def __init__(self, date_range: DateRange) -> None:
        """Initialize with date range.

        Args:
            date_range: The date range to filter by (inclusive).
        """
        self._date_range = date_range

    def matches(self, message: Message) -> bool:
        """Check if message timestamp is within range.

        Args:
            message: Message to check.

        Returns:
            True if message timestamp falls within the date range.
        """
        return self._date_range.contains(message.timestamp)

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        """Filter messages by date range.

        Args:
            messages: Iterable of messages to filter.

        Yields:
            Messages within the date range.
        """
        for msg in messages:
            if self.matches(msg):
                yield msg
