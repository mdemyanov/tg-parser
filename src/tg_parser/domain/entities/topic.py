"""Topic entity for forum-style supergroups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tg_parser.domain.value_objects.identifiers import TopicId


@dataclass(frozen=True, slots=True)
class Topic:
    """Forum topic in a supergroup.

    Topics are sub-forums within a Telegram supergroup when forum mode is enabled.
    """

    id: TopicId
    title: str
    created_at: datetime | None = None
    is_general: bool = False
