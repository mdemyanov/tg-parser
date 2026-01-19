"""Domain entities."""

from __future__ import annotations

from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.chunk import Chunk, ChunkMetadata
from tg_parser.domain.entities.message import (
    Attachment,
    Message,
    MessageType,
    ReplyInfo,
)
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.entities.topic import Topic

__all__ = [
    "Attachment",
    "Chat",
    "ChatType",
    "Chunk",
    "ChunkMetadata",
    "Message",
    "MessageType",
    "Participant",
    "ReplyInfo",
    "Topic",
]
