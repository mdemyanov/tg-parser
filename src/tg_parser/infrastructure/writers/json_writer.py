"""JSON writer for structured output."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tg_parser.infrastructure.token_counters import get_token_counter

if TYPE_CHECKING:
    from tg_parser.domain.entities.chat import Chat
    from tg_parser.domain.entities.message import Message


class JSONWriter:
    """Write chat data to structured JSON format.

    Preserves all message fields for programmatic processing.
    """

    def __init__(
        self,
        indent: int = 2,
        include_extraction_guide: bool = False,
    ) -> None:
        """Initialize JSON writer.

        Args:
            indent: JSON indentation level. Set to 0 for compact output.
            include_extraction_guide: Whether to include extraction guide in metadata.
        """
        self._indent = indent if indent > 0 else None
        self._include_extraction_guide = include_extraction_guide
        self._token_counter = get_token_counter()

    def write(self, chat: Chat, destination: Path) -> None:
        """Write entire chat to JSON file.

        Args:
            chat: Chat entity to write.
            destination: Path to output file.
        """
        content = self.format_to_string(chat)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def write_messages(
        self,
        messages: list[Message],
        destination: Path,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Write subset of messages with optional metadata.

        Args:
            messages: List of messages to write.
            destination: Path to output file.
            metadata: Optional metadata to include in output.
        """
        data = self._build_messages_data(messages, metadata)
        content = json.dumps(data, indent=self._indent, ensure_ascii=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def format_to_string(self, chat: Chat) -> str:
        """Format chat to JSON string without writing to file.

        Args:
            chat: Chat entity to format.

        Returns:
            Formatted JSON string.
        """
        data = self._build_chat_data(chat)
        return json.dumps(data, indent=self._indent, ensure_ascii=False)

    def _build_chat_data(self, chat: Chat) -> dict[str, Any]:
        """Build complete chat data structure."""
        # Calculate date range
        date_range_data: dict[str, str | None] | None = None
        if chat.date_range:
            start, end = chat.date_range
            date_range_data = {
                "start": start.isoformat(),
                "end": end.isoformat(),
            }

        # Estimate tokens
        estimated_tokens = self._token_counter.count_messages(chat.messages)

        # Build meta
        meta: dict[str, Any] = {
            "chat_name": chat.name,
            "chat_type": chat.chat_type.value,
            "exported_at": datetime.now().isoformat(),
            "date_range": date_range_data,
            "message_count": len(chat.messages),
            "estimated_tokens": estimated_tokens,
        }

        # Add extraction guide if requested
        if self._include_extraction_guide:
            from tg_parser.domain.constants import EXTRACTION_GUIDE_RU

            meta["extraction_guide"] = EXTRACTION_GUIDE_RU.strip()

        return {
            "meta": meta,
            "participants": self._format_participants(chat),
            "topics": self._format_topics(chat),
            "messages": [self._format_message(msg) for msg in chat.messages],
        }

    def _build_messages_data(
        self, messages: list[Message], metadata: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Build messages-only data structure."""
        # Calculate date range from messages
        date_range_data: dict[str, str | None] | None = None
        if messages:
            timestamps = [m.timestamp for m in messages]
            date_range_data = {
                "start": min(timestamps).isoformat(),
                "end": max(timestamps).isoformat(),
            }

        estimated_tokens = self._token_counter.count_messages(messages)

        meta: dict[str, Any] = {
            "exported_at": datetime.now().isoformat(),
            "date_range": date_range_data,
            "message_count": len(messages),
            "estimated_tokens": estimated_tokens,
        }

        if metadata:
            meta.update(metadata)

        return {
            "meta": meta,
            "messages": [self._format_message(msg) for msg in messages],
        }

    def _format_participants(self, chat: Chat) -> list[dict[str, Any]]:
        """Format participants list sorted by message count."""
        return [
            {
                "id": p.id,
                "name": p.name,
                "username": p.username,
                "message_count": p.message_count,
            }
            for p in sorted(
                chat.participants.values(),
                key=lambda x: x.message_count,
                reverse=True,
            )
        ]

    def _format_topics(self, chat: Chat) -> list[dict[str, Any]]:
        """Format topics list."""
        result: list[dict[str, Any]] = []
        for topic in chat.topics.values():
            created = topic.created_at.isoformat() if topic.created_at else None
            result.append(
                {
                    "id": topic.id,
                    "title": topic.title,
                    "is_general": topic.is_general,
                    "created_at": created,
                }
            )
        return result

    def _format_message(self, msg: Message) -> dict[str, Any]:
        """Format single message."""
        data: dict[str, Any] = {
            "id": msg.id,
            "timestamp": msg.timestamp.isoformat(),
            "author_id": msg.author_id,
            "author_name": msg.author_name,
            "text": msg.text,
            "message_type": msg.message_type.value,
            "topic_id": msg.topic_id,
            "reply_to": self._format_reply_to(msg),
            "forward_from": msg.forward_from,
            "mentions": list(msg.mentions) if msg.mentions else [],
            "reactions": msg.reactions if msg.reactions else {},
            "attachments": self._format_attachments(msg),
        }
        return data

    def _format_reply_to(self, msg: Message) -> dict[str, Any] | None:
        """Format reply_to information."""
        if not msg.reply_to:
            return None
        return {
            "message_id": msg.reply_to.message_id,
            "author": msg.reply_to.author,
            "preview": msg.reply_to.preview,
        }

    def _format_attachments(self, msg: Message) -> list[dict[str, Any]]:
        """Format attachments list."""
        return [
            {
                "type": att.type,
                "file_name": att.file_name,
                "file_path": att.file_path,
                "mime_type": att.mime_type,
                "size_bytes": att.size_bytes,
            }
            for att in msg.attachments
        ]
