"""Participant entity representing a chat member."""

from __future__ import annotations

from dataclasses import dataclass

from tg_parser.domain.value_objects.identifiers import UserId


@dataclass(frozen=True, slots=True)
class Participant:
    """Chat participant with aggregated statistics."""

    id: UserId
    name: str
    username: str | None = None
    message_count: int = 0
