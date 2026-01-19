"""Get mentions analysis use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime  # noqa: TC003 - used at runtime in dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tg_parser.domain.entities.chat import Chat
    from tg_parser.domain.entities.participant import Participant


@dataclass
class MentionInfo:
    """Information about a mentioned user."""

    mention: str
    count: int
    participant_match: Participant | None
    first_mention: datetime
    last_mention: datetime


@dataclass
class MentionsResult:
    """Result of mentions analysis."""

    chat_name: str
    date_range: tuple[datetime, datetime] | None
    total_mentions: int
    unique_users: int
    mentions: list[MentionInfo]


class GetMentionsUseCase:
    """Use case for analyzing mentions in a chat."""

    def execute(
        self,
        chat: Chat,
        min_count: int = 1,
    ) -> MentionsResult:
        """Analyze mentions in chat messages.

        Args:
            chat: Chat entity to analyze.
            min_count: Minimum mention count to include.

        Returns:
            MentionsResult with mention statistics.
        """
        # Collect all mentions with timestamps
        mention_data: dict[str, list[datetime]] = {}

        for msg in chat.messages:
            for mention in msg.mentions:
                normalized = self._normalize_mention(mention)
                if normalized not in mention_data:
                    mention_data[normalized] = []
                mention_data[normalized].append(msg.timestamp)

        # Build MentionInfo list
        mentions: list[MentionInfo] = []
        for mention, timestamps in mention_data.items():
            if len(timestamps) < min_count:
                continue

            participant = self._find_participant_match(mention, chat)

            mentions.append(
                MentionInfo(
                    mention=mention,
                    count=len(timestamps),
                    participant_match=participant,
                    first_mention=min(timestamps),
                    last_mention=max(timestamps),
                )
            )

        # Sort by count descending
        mentions.sort(key=lambda x: x.count, reverse=True)

        return MentionsResult(
            chat_name=chat.name,
            date_range=chat.date_range,
            total_mentions=sum(m.count for m in mentions),
            unique_users=len(mentions),
            mentions=mentions,
        )

    def _normalize_mention(self, mention: str) -> str:
        """Normalize mention string (remove @ prefix, lowercase)."""
        return mention.lstrip("@").lower()

    def _find_participant_match(
        self,
        mention: str,
        chat: Chat,
    ) -> Participant | None:
        """Find matching participant by username or name.

        Matching strategy:
        1. Exact username match (case-insensitive)
        2. Partial name match (mention contained in participant name)
        """
        mention_lower = mention.lower()

        for participant in chat.participants.values():
            # Check username (exact match)
            if participant.username and participant.username.lower() == mention_lower:
                return participant

            # Check name (partial match)
            if mention_lower in participant.name.lower():
                return participant

        return None
