"""Knowledge Base template writer with YAML frontmatter and WikiLinks."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from tg_parser.infrastructure.token_counters import get_token_counter

if TYPE_CHECKING:
    from tg_parser.domain.entities.chat import Chat
    from tg_parser.domain.entities.message import Message


class KBTemplateWriter:
    """Write chat data to Knowledge Base template format.

    Features:
    - YAML frontmatter with metadata
    - WikiLinks for participants in message headers: [[user_id|Display Name]]
    - Preserves @mentions as-is in message body
    - Suitable for Obsidian, Logseq, and other knowledge bases
    """

    def __init__(
        self,
        include_reactions: bool = True,
        include_attachments: bool = True,
        include_extraction_guide: bool = False,
        timestamp_format: str = "%H:%M",
        date_format: str = "%Y-%m-%d",
    ) -> None:
        """Initialize KB template writer.

        Args:
            include_reactions: Whether to include reactions in output.
            include_attachments: Whether to include attachment info.
            include_extraction_guide: Whether to append extraction guide template.
            timestamp_format: Format for message timestamps.
            date_format: Format for date headers.
        """
        self._include_reactions = include_reactions
        self._include_attachments = include_attachments
        self._include_extraction_guide = include_extraction_guide
        self._timestamp_format = timestamp_format
        self._date_format = date_format
        self._token_counter = get_token_counter()

    def write(self, chat: Chat, destination: Path) -> None:
        """Write entire chat to KB template file.

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
            metadata: Optional metadata to include in frontmatter.
        """
        lines: list[str] = []

        # Build frontmatter from messages
        frontmatter = self._build_messages_frontmatter(messages, metadata)
        lines.append(self._format_frontmatter(frontmatter))
        lines.append("")

        # Format messages
        participants_map = self._get_participants_map(messages)
        lines.extend(self._format_messages(messages, participants_map))

        content = "\n".join(lines)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def format_to_string(self, chat: Chat) -> str:
        """Format chat to string without writing to file.

        Args:
            chat: Chat entity to format.

        Returns:
            Formatted KB template string.
        """
        return self._format_chat(chat)

    def _format_chat(self, chat: Chat) -> str:
        """Format entire chat to KB template."""
        lines: list[str] = []

        # YAML frontmatter
        frontmatter = self._build_chat_frontmatter(chat)
        lines.append(self._format_frontmatter(frontmatter))
        lines.append("")

        # Header
        lines.append(f"# Chat: {chat.name}")
        lines.append("")

        # Build participants map for WikiLinks
        participants_map: dict[str, str] = {
            p.id: p.name for p in chat.participants.values()
        }

        # Messages grouped by date
        lines.extend(self._format_messages(chat.messages, participants_map))

        # Extraction guide
        if self._include_extraction_guide:
            from tg_parser.domain.constants import EXTRACTION_GUIDE_RU

            lines.append(EXTRACTION_GUIDE_RU)

        return "\n".join(lines)

    def _build_chat_frontmatter(self, chat: Chat) -> dict[str, Any]:
        """Build frontmatter data from chat."""
        estimated_tokens = self._token_counter.count_messages(chat.messages)

        # Build participants with WikiLinks
        sorted_participants = sorted(
            chat.participants.values(),
            key=lambda x: x.message_count,
            reverse=True,
        )
        participants_wikilinks = [f"[[{p.id}|{p.name}]]" for p in sorted_participants]

        # Date range
        date_range_str: str | None = None
        if chat.date_range:
            start, end = chat.date_range
            start_str = start.strftime(self._date_format)
            end_str = end.strftime(self._date_format)
            date_range_str = f"{start_str} — {end_str}"

        frontmatter: dict[str, Any] = {
            "title": f"Chat Export - {chat.name}",
            "date": datetime.now().strftime(self._date_format),
            "chat_type": chat.chat_type.value,
            "participants": participants_wikilinks,
            "date_range": date_range_str,
            "message_count": len(chat.messages),
            "estimated_tokens": estimated_tokens,
            "tags": ["telegram-export"],
        }

        # Add single topic if all messages belong to one topic
        topic_ids = {m.topic_id for m in chat.messages if m.topic_id is not None}
        if len(topic_ids) == 1:
            topic_id = topic_ids.pop()
            if topic_id in chat.topics:
                frontmatter["topic"] = chat.topics[topic_id].title

        return frontmatter

    def _build_messages_frontmatter(
        self, messages: list[Message], metadata: dict[str, Any] | None
    ) -> dict[str, Any]:
        """Build frontmatter from messages subset."""
        estimated_tokens = self._token_counter.count_messages(messages)

        # Build participants map from messages
        participants_map = self._get_participants_map(messages)
        participants_wikilinks = [
            f"[[{uid}|{name}]]" for uid, name in participants_map.items()
        ]

        # Date range
        date_range_str: str | None = None
        if messages:
            timestamps = [m.timestamp for m in messages]
            start, end = min(timestamps), max(timestamps)
            start_str = start.strftime(self._date_format)
            end_str = end.strftime(self._date_format)
            date_range_str = f"{start_str} — {end_str}"

        title = "Chat Export"
        if metadata and "title" in metadata:
            title = metadata["title"]

        frontmatter: dict[str, Any] = {
            "title": title,
            "date": datetime.now().strftime(self._date_format),
            "participants": participants_wikilinks,
            "date_range": date_range_str,
            "message_count": len(messages),
            "estimated_tokens": estimated_tokens,
            "tags": ["telegram-export"],
        }

        # Add metadata fields
        if metadata:
            for key in ("chat_type", "topic", "chat_name"):
                if key in metadata:
                    frontmatter[key] = metadata[key]

        return frontmatter

    def _get_participants_map(self, messages: list[Message]) -> dict[str, str]:
        """Extract participants map from messages."""
        participants: dict[str, str] = {}
        for msg in messages:
            if msg.author_id not in participants:
                participants[msg.author_id] = msg.author_name
        return participants

    def _format_frontmatter(self, data: dict[str, Any]) -> str:
        """Format frontmatter as YAML."""
        lines = ["---"]
        for key, value in data.items():
            if value is None:
                continue
            if isinstance(value, list):
                lines.append(f"{key}:")
                for item in value:
                    # Escape quotes in YAML
                    lines.append(f'  - "{item}"')
            elif isinstance(value, str):
                # Quote strings that might need escaping
                if ":" in value or '"' in value or value.startswith("-"):
                    lines.append(f'{key}: "{value}"')
                else:
                    lines.append(f"{key}: {value}")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        return "\n".join(lines)

    def _format_messages(
        self,
        messages: list[Message],
        participants_map: dict[str, str],  # noqa: ARG002
    ) -> list[str]:
        """Format messages grouped by date."""
        lines: list[str] = []
        current_date: date | None = None

        for msg in messages:
            msg_date = msg.timestamp.date()

            # New date header
            if current_date != msg_date:
                if current_date is not None:
                    lines.append("")
                    lines.append("---")
                    lines.append("")
                lines.append(f"## {msg_date.strftime(self._date_format)}")
                lines.append("")
                current_date = msg_date

            # Message with WikiLink in header
            lines.extend(self._format_message(msg))
            lines.append("")

        return lines

    def _format_message(self, msg: Message) -> list[str]:
        """Format single message with WikiLink header."""
        lines: list[str] = []

        # Header: time + author with WikiLink
        time_str = msg.timestamp.strftime(self._timestamp_format)
        author_wikilink = f"[[{msg.author_id}|{msg.author_name}]]"
        lines.append(f"### {time_str} — {author_wikilink}")

        # Reply quote (no WikiLink in body, just plain text)
        if msg.reply_to:
            if msg.reply_to.preview:
                lines.append(f"> {msg.reply_to.preview}")
            elif msg.reply_to.author:
                lines.append(f"> Reply to {msg.reply_to.author}")
            else:
                lines.append(f"> Reply to message #{msg.reply_to.message_id}")

        # Forward info
        if msg.forward_from:
            lines.append(f"*Forwarded from {msg.forward_from}*")

        # Main text - preserve @mentions as-is
        if msg.text.strip():
            lines.append(msg.text)

        # Attachments
        if self._include_attachments and msg.attachments:
            for att in msg.attachments:
                if att.file_name:
                    lines.append(f"[Attachment: {att.type} - {att.file_name}]")
                else:
                    lines.append(f"[Attachment: {att.type}]")

        # Reactions
        if self._include_reactions and msg.reactions:
            reactions_str = " ".join(
                f"{emoji} {count}" for emoji, count in msg.reactions.items()
            )
            lines.append(f"*Reactions: {reactions_str}*")

        return lines
