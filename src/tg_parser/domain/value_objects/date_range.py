"""DateRange value object for filtering by time period."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class DateRange:
    """Immutable date range for filtering messages by time period.

    Both start and end are inclusive. If None, that bound is open.
    """

    start: datetime | None = None
    end: datetime | None = None

    def __post_init__(self) -> None:
        """Validate that start <= end if both are set."""
        if self.start and self.end and self.start > self.end:
            msg = f"start ({self.start}) must be before or equal to end ({self.end})"
            raise ValueError(msg)

    def contains(self, dt: datetime) -> bool:
        """Check if datetime falls within range (inclusive)."""
        if self.start and dt < self.start:
            return False
        return not (self.end and dt > self.end)

    def is_empty(self) -> bool:
        """Check if no bounds are set (matches everything)."""
        return self.start is None and self.end is None
