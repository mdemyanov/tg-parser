"""Message filters."""

from __future__ import annotations

from tg_parser.infrastructure.filters.composite import CompositeFilter, build_filter
from tg_parser.infrastructure.filters.date_filter import DateFilter
from tg_parser.infrastructure.filters.sender_filter import SenderFilter

__all__ = [
    "CompositeFilter",
    "DateFilter",
    "SenderFilter",
    "build_filter",
]
