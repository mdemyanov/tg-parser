"""Sender filter for messages."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.value_objects.identifiers import UserId


class SenderFilter:
    """Filter messages by sender name or ID."""

    def __init__(
        self,
        include_names: frozenset[str] | None = None,
        include_ids: frozenset[UserId] | None = None,
        exclude_names: frozenset[str] | None = None,
    ) -> None:
        """Initialize sender filter.

        Args:
            include_names: Names to include (partial match, case-insensitive).
            include_ids: User IDs to include (exact match).
            exclude_names: Names to exclude (partial match, case-insensitive).
        """
        # Normalize names to lowercase for case-insensitive matching
        self._include_names = (
            frozenset(n.lower() for n in include_names) if include_names else None
        )
        self._include_ids = include_ids
        self._exclude_names = (
            frozenset(n.lower() for n in exclude_names) if exclude_names else None
        )

    def matches(self, message: Message) -> bool:
        """Check if message matches sender criteria.

        Args:
            message: Message to check.

        Returns:
            True if message passes the sender filter.
        """
        author_lower = message.author_name.lower()

        # Check exclusions first
        if self._exclude_names:
            for exclude in self._exclude_names:
                if exclude in author_lower:
                    return False

        # If no inclusions specified, message passes (after exclusions)
        if not self._include_names and not self._include_ids:
            return True

        # Check ID match
        if self._include_ids and message.author_id in self._include_ids:
            return True

        # Check name match (partial, case-insensitive)
        if self._include_names:
            for name in self._include_names:
                if name in author_lower:
                    return True

        return False

    def filter(self, messages: Iterable[Message]) -> Iterator[Message]:
        """Filter messages by sender.

        Args:
            messages: Iterable of messages to filter.

        Yields:
            Messages that pass the sender filter.
        """
        for msg in messages:
            if self.matches(msg):
                yield msg
