"""Chat aggregate entity - root entity containing all chat data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from tg_parser.domain.entities.message import Message
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.value_objects.identifiers import TopicId, UserId


class ChatType(Enum):
    """Types of Telegram chats."""

    PERSONAL = "personal"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    SUPERGROUP_FORUM = "supergroup_forum"
    CHANNEL = "channel"


# Mapping from Telegram JSON type strings to ChatType
TELEGRAM_TYPE_MAP: dict[str, ChatType] = {
    "personal_chat": ChatType.PERSONAL,
    "private_group": ChatType.GROUP,
    "private_supergroup": ChatType.SUPERGROUP,
    "public_supergroup": ChatType.SUPERGROUP,
    "public_channel": ChatType.CHANNEL,
    "private_channel": ChatType.CHANNEL,
}


@dataclass
class Chat:
    """Chat aggregate - the root entity containing all chat data.

    Not frozen because it aggregates mutable collections,
    but individual entities (Message, Topic, Participant) are immutable.
    """

    id: int
    name: str
    chat_type: ChatType
    messages: list[Message] = field(default_factory=lambda: [])
    topics: dict[TopicId, Topic] = field(default_factory=lambda: {})
    participants: dict[UserId, Participant] = field(default_factory=lambda: {})

    @property
    def is_forum(self) -> bool:
        """Check if this is a forum-style supergroup with topics."""
        return self.chat_type == ChatType.SUPERGROUP_FORUM

    @property
    def date_range(self) -> tuple[datetime, datetime] | None:
        """Get the time range of messages (min, max timestamps)."""
        if not self.messages:
            return None
        timestamps = [m.timestamp for m in self.messages]
        return min(timestamps), max(timestamps)

    @property
    def message_count(self) -> int:
        """Total number of messages."""
        return len(self.messages)

    def messages_by_topic(self, topic_id: TopicId) -> list[Message]:
        """Get all messages belonging to a specific topic."""
        return [m for m in self.messages if m.topic_id == topic_id]

    def messages_by_author(self, author_id: UserId) -> list[Message]:
        """Get all messages from a specific author."""
        return [m for m in self.messages if m.author_id == author_id]

    def get_topic(self, topic_id: TopicId) -> Topic | None:
        """Get topic by ID."""
        return self.topics.get(topic_id)

    def get_participant(self, user_id: UserId) -> Participant | None:
        """Get participant by ID."""
        return self.participants.get(user_id)
