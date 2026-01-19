"""Telegram Desktop JSON export reader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.message import Message
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.exceptions import InvalidExportError
from tg_parser.domain.value_objects.identifiers import TopicId, UserId
from tg_parser.infrastructure.readers._parsing import (
    determine_chat_type,
    extract_topics,
    parse_message,
)


class TelegramJSONReader:
    """Reader for Telegram Desktop JSON exports."""

    def read(self, source: Path) -> Chat:
        """Read and parse Telegram JSON export.

        Args:
            source: Path to result.json from Telegram Desktop export.

        Returns:
            Chat entity with all messages, topics, and participants.

        Raises:
            FileNotFoundError: If source file doesn't exist.
            InvalidExportError: If JSON structure doesn't match Telegram format.
        """
        if not source.exists():
            raise FileNotFoundError(f"Export file not found: {source}")

        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise InvalidExportError(source, f"Invalid JSON: {e}") from e

        return self._parse_chat(data, source)

    def validate(self, source: Path) -> list[str]:
        """Validate export and return list of warnings.

        Args:
            source: Path to result.json file.

        Returns:
            List of warning messages (empty if valid).
        """
        warnings: list[str] = []

        if not source.exists():
            warnings.append(f"File not found: {source}")
            return warnings

        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            warnings.append(f"Invalid JSON: {e}")
            return warnings

        if "messages" not in data:
            warnings.append("Missing 'messages' field")
        if "name" not in data:
            warnings.append("Missing 'name' field")
        if "type" not in data:
            warnings.append("Missing 'type' field")

        return warnings

    def _parse_chat(self, data: dict[str, Any], source: Path) -> Chat:
        """Parse chat data into Chat entity."""
        if "messages" not in data:
            raise InvalidExportError(source, "Missing 'messages' field")

        chat_type = determine_chat_type(data)
        topics: dict[TopicId, Topic] = {}
        participants: dict[UserId, Participant] = {}
        messages: list[Message] = []

        raw_messages: list[dict[str, Any]] = data.get("messages", [])

        # First pass: extract topics from service messages
        if chat_type in (ChatType.SUPERGROUP, ChatType.SUPERGROUP_FORUM):
            topics = extract_topics(raw_messages)
            if topics and len(topics) > 1:  # More than just General topic
                chat_type = ChatType.SUPERGROUP_FORUM

        # Second pass: parse all messages
        for raw_msg in raw_messages:
            msg = parse_message(raw_msg, topics)
            if msg:
                messages.append(msg)
                self._update_participant(participants, msg)

        return Chat(
            id=data.get("id", 0),
            name=data.get("name", "Unknown"),
            chat_type=chat_type,
            messages=messages,
            topics=topics,
            participants=participants,
        )

    def _update_participant(
        self,
        participants: dict[UserId, Participant],
        msg: Message,
    ) -> None:
        """Update or add participant based on message."""
        if msg.author_id not in participants:
            participants[msg.author_id] = Participant(
                id=msg.author_id,
                name=msg.author_name,
                message_count=1,
            )
        else:
            # Create new immutable Participant with incremented count
            old = participants[msg.author_id]
            participants[msg.author_id] = Participant(
                id=old.id,
                name=old.name,
                username=old.username,
                message_count=old.message_count + 1,
            )
