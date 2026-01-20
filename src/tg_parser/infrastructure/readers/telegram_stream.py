"""Streaming reader for large Telegram exports using ijson.

This module provides memory-efficient parsing of large Telegram JSON exports
by using incremental JSON parsing via ijson library.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from tg_parser.domain.entities.chat import Chat, ChatType
from tg_parser.domain.entities.message import Message
from tg_parser.domain.entities.participant import Participant
from tg_parser.domain.entities.topic import Topic
from tg_parser.domain.exceptions import InvalidExportError
from tg_parser.domain.value_objects.identifiers import (
    GENERAL_TOPIC_ID,
    TopicId,
    UserId,
)
from tg_parser.infrastructure.readers._parsing import (
    determine_chat_type,
    parse_datetime,
    parse_message,
)

# Progress callback type: (current_messages, total_estimated)
ProgressCallback = Callable[[int, int], None]


class TelegramStreamReader:
    """Streaming reader for large Telegram JSON exports.

    Uses ijson for memory-efficient parsing of large files.
    Implements both ChatReaderProtocol and StreamingReaderProtocol.

    Example:
        >>> reader = TelegramStreamReader()
        >>> chat = reader.read(Path("./large_export.json"))

        # With progress callback:
        >>> def on_progress(current, total):
        ...     print(f"Processed {current}/{total} messages")
        >>> reader = TelegramStreamReader(progress_callback=on_progress)
        >>> chat = reader.read(Path("./large_export.json"))
    """

    def __init__(
        self,
        progress_callback: ProgressCallback | None = None,
        progress_interval: int = 100,
    ) -> None:
        """Initialize streaming reader.

        Args:
            progress_callback: Optional callback(current, total) for progress.
            progress_interval: Report progress every N messages.
        """
        self._progress_callback = progress_callback
        self._progress_interval = progress_interval
        self._ensure_ijson()

    def _ensure_ijson(self) -> None:
        """Ensure ijson is available."""
        try:
            import ijson  # noqa: F401
        except ImportError as e:
            msg = (
                "ijson is required for streaming. "
                "Install with: uv pip install 'tg-parser[streaming]'"
            )
            raise ImportError(msg) from e

    def read(self, source: Path) -> Chat:
        """Read entire chat using streaming (memory-efficient).

        Uses two-pass algorithm:
        1. Extract metadata and topics
        2. Stream messages with topic context

        Args:
            source: Path to Telegram JSON export.

        Returns:
            Chat entity with all messages, topics, and participants.

        Raises:
            FileNotFoundError: If source doesn't exist.
            InvalidExportError: If JSON structure is invalid.
        """
        if not source.exists():
            raise FileNotFoundError(f"Export file not found: {source}")

        # Extract metadata and topics (Pass 1)
        metadata = self._extract_metadata(source)
        topics = self._extract_topics(source)

        # Determine chat type
        chat_type = determine_chat_type(metadata)
        if topics and len(topics) > 1:
            chat_type = ChatType.SUPERGROUP_FORUM

        # Count messages for progress (optional fast pass)
        total_messages = 0
        if self._progress_callback:
            total_messages = self._count_messages(source)

        # Stream messages (Pass 2)
        messages: list[Message] = []
        participants: dict[UserId, Participant] = {}

        for idx, msg in enumerate(self.stream_messages(source, topics)):
            messages.append(msg)
            self._update_participant(participants, msg)

            # Report progress
            if self._progress_callback and (idx + 1) % self._progress_interval == 0:
                self._progress_callback(idx + 1, total_messages)

        # Final progress report
        if self._progress_callback and messages:
            self._progress_callback(len(messages), total_messages or len(messages))

        return Chat(
            id=metadata.get("id", 0),
            name=metadata.get("name", "Unknown"),
            chat_type=chat_type,
            messages=messages,
            topics=topics,
            participants=participants,
        )

    def stream_messages(
        self,
        source: Path,
        topics: dict[TopicId, Topic] | None = None,
    ) -> Iterator[Message]:
        """Stream messages without loading entire file.

        Args:
            source: Path to JSON export.
            topics: Pre-extracted topics map (optional, extracts if None).

        Yields:
            Message entities one by one.
        """
        import ijson

        if topics is None:
            topics = self._extract_topics(source)

        with source.open("rb") as f:
            for raw in ijson.items(f, "messages.item"):
                raw_dict: dict[str, Any] = raw
                msg = parse_message(raw_dict, topics)
                if msg:
                    yield msg

    def validate(self, source: Path) -> list[str]:
        """Validate export format (streaming-compatible).

        Args:
            source: Path to JSON export.

        Returns:
            List of warning messages (empty if valid).
        """
        import ijson

        warnings: list[str] = []

        if not source.exists():
            warnings.append(f"File not found: {source}")
            return warnings

        try:
            with source.open("rb") as f:
                # Check for required top-level keys
                found_keys: set[str] = set()
                parser = ijson.parse(f)

                for prefix, event, value in parser:
                    if event == "map_key" and prefix == "":
                        found_keys.add(str(value))
                    # Stop after finding top-level structure
                    if len(found_keys) >= 5:
                        break

                if "messages" not in found_keys:
                    warnings.append("Missing 'messages' field")
                if "name" not in found_keys:
                    warnings.append("Missing 'name' field")
                if "type" not in found_keys:
                    warnings.append("Missing 'type' field")

        except Exception as e:
            warnings.append(f"Parse error: {e}")

        return warnings

    def _extract_metadata(self, source: Path) -> dict[str, Any]:
        """Extract top-level metadata (id, name, type).

        Args:
            source: Path to JSON export.

        Returns:
            Dict with metadata fields.
        """
        import ijson

        metadata: dict[str, Any] = {}

        try:
            with source.open("rb") as f:
                parser = ijson.parse(f)

                for prefix, event, value in parser:
                    # Top-level scalar values
                    if prefix in ("id", "name", "type") and event in (
                        "string",
                        "number",
                    ):
                        metadata[prefix] = value

                    # Stop when we hit messages array
                    if prefix == "messages" and event == "start_array":
                        break

        except Exception as e:
            raise InvalidExportError(source, f"Failed to parse metadata: {e}") from e

        return metadata

    def _extract_topics(self, source: Path) -> dict[TopicId, Topic]:
        """Extract topics from service messages (streaming).

        Args:
            source: Path to JSON export.

        Returns:
            Dict mapping TopicId to Topic entity.
        """
        import ijson

        topics: dict[TopicId, Topic] = {}

        with source.open("rb") as f:
            for raw in ijson.items(f, "messages.item"):
                raw_dict: dict[str, Any] = raw
                if raw_dict.get("type") != "service":
                    continue

                action = raw_dict.get("action", "")

                if action == "topic_created":
                    topic_id = TopicId(raw_dict.get("id", 0))
                    topics[topic_id] = Topic(
                        id=topic_id,
                        title=raw_dict.get("title", "Unknown"),
                        created_at=parse_datetime(raw_dict.get("date")),
                        is_general=False,
                    )

                elif action == "topic_edit":
                    new_title = raw_dict.get("new_title", "")
                    if new_title and GENERAL_TOPIC_ID not in topics:
                        topics[GENERAL_TOPIC_ID] = Topic(
                            id=GENERAL_TOPIC_ID,
                            title=new_title,
                            created_at=parse_datetime(raw_dict.get("date")),
                            is_general=True,
                        )

        # Ensure General topic exists if we have other topics
        if topics and GENERAL_TOPIC_ID not in topics:
            topics[GENERAL_TOPIC_ID] = Topic(
                id=GENERAL_TOPIC_ID,
                title="General",
                is_general=True,
            )

        return topics

    def _count_messages(self, source: Path) -> int:
        """Fast count of messages for progress estimation.

        Uses ijson.parse() which only tracks structure, not values,
        making this pass very fast and memory-efficient.

        Args:
            source: Path to JSON export.

        Returns:
            Total message count.
        """
        import ijson

        count = 0
        with source.open("rb") as f:
            parser = ijson.parse(f)
            for prefix, event, _ in parser:
                if prefix == "messages.item" and event == "start_map":
                    count += 1
        return count

    def _update_participant(
        self,
        participants: dict[UserId, Participant],
        msg: Message,
    ) -> None:
        """Update participant stats from message.

        Args:
            participants: Participants dict to update.
            msg: Message to extract participant from.
        """
        if msg.author_id not in participants:
            participants[msg.author_id] = Participant(
                id=msg.author_id,
                name=msg.author_name,
                message_count=1,
            )
        else:
            old = participants[msg.author_id]
            participants[msg.author_id] = Participant(
                id=old.id,
                name=old.name,
                username=old.username,
                message_count=old.message_count + 1,
            )
