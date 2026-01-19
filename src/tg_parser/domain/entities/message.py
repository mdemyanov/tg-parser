"""Message entity - core unit of conversation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from tg_parser.domain.value_objects.identifiers import MessageId, TopicId, UserId


class MessageType(Enum):
    """Types of Telegram messages."""

    TEXT = "text"
    SERVICE = "service"
    MEDIA = "media"
    STICKER = "sticker"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"


@dataclass(frozen=True, slots=True)
class Attachment:
    """Media attachment metadata."""

    type: str  # photo, video, document, voice_message, etc.
    file_path: str | None = None
    file_name: str | None = None
    mime_type: str | None = None
    size_bytes: int | None = None


@dataclass(frozen=True, slots=True)
class ReplyInfo:
    """Information about replied-to message."""

    message_id: MessageId
    author: str | None = None
    preview: str | None = None


@dataclass(frozen=True, slots=True)
class Message:
    """Core message entity - a single unit of conversation.

    Immutable to ensure thread safety and predictable behavior.
    """

    id: MessageId
    timestamp: datetime
    author_name: str
    author_id: UserId
    text: str
    message_type: MessageType = MessageType.TEXT
    topic_id: TopicId | None = None
    reply_to: ReplyInfo | None = None
    forward_from: str | None = None
    mentions: tuple[str, ...] = field(default_factory=lambda: ())
    attachments: tuple[Attachment, ...] = field(default_factory=lambda: ())
    reactions: dict[str, int] = field(default_factory=lambda: {})

    @property
    def has_text(self) -> bool:
        """Check if message has meaningful text content."""
        return bool(self.text.strip())

    @property
    def is_service(self) -> bool:
        """Check if this is a service/system message."""
        return self.message_type == MessageType.SERVICE

    @property
    def is_forward(self) -> bool:
        """Check if this is a forwarded message."""
        return self.forward_from is not None

    @property
    def has_attachments(self) -> bool:
        """Check if message has any attachments."""
        return len(self.attachments) > 0

    @property
    def has_reactions(self) -> bool:
        """Check if message has any reactions."""
        return bool(self.reactions)

    @property
    def total_reactions(self) -> int:
        """Get total reaction count."""
        return sum(self.reactions.values())
