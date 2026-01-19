"""Filter protocol for message filtering."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message


class FilterProtocol(Protocol):
    """Protocol for message filtering."""

    def matches(self, message: Message) -> bool:
        """Check if message matches filter criteria.

        Args:
            message: Message to check.

        Returns:
            True if message passes the filter.
        """
        ...

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        """Filter messages lazily (generator).

        Args:
            messages: Iterable of messages to filter.

        Yields:
            Messages that pass the filter.
        """
        ...
