"""FilterSpecification value object for message filtering criteria."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from tg_parser.domain.value_objects.date_range import DateRange
from tg_parser.domain.value_objects.identifiers import UserId


@dataclass(frozen=True)
class FilterSpecification:
    """Immutable specification for message filtering.

    All filter criteria are combined with AND logic.
    Empty collections mean "no filter" for that criterion.
    """

    # Time-based filters
    date_range: DateRange | None = None

    # Sender filters (names matched case-insensitively, partial match)
    senders: frozenset[str] = field(default_factory=lambda: frozenset())
    sender_ids: frozenset[UserId] = field(default_factory=lambda: frozenset())
    exclude_senders: frozenset[str] = field(default_factory=lambda: frozenset())

    # Topic filters (names matched case-insensitively, partial match)
    topics: frozenset[str] = field(default_factory=lambda: frozenset())
    exclude_topics: frozenset[str] = field(default_factory=lambda: frozenset())

    # Content filters
    mentions: frozenset[str] = field(default_factory=lambda: frozenset())
    content_pattern: re.Pattern[str] | None = None
    min_length: int = 0

    # Type filters
    has_attachment: bool | None = None
    has_reactions: bool | None = None
    exclude_forwards: bool = False
    exclude_service: bool = True  # Default: exclude service messages
    exclude_empty: bool = True  # Default: exclude empty messages

    def is_empty(self) -> bool:
        """Check if no meaningful filters are applied (besides defaults)."""
        return (
            self.date_range is None
            and not self.senders
            and not self.sender_ids
            and not self.exclude_senders
            and not self.topics
            and not self.exclude_topics
            and not self.mentions
            and self.content_pattern is None
            and self.min_length == 0
            and self.has_attachment is None
            and self.has_reactions is None
            and not self.exclude_forwards
            # exclude_service and exclude_empty are defaults,
            # don't count as "active" filters
        )
