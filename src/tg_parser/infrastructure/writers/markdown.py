"""Markdown writer for LLM-optimized output."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from tg_parser.domain.entities.chat import Chat
from tg_parser.domain.entities.message import Message


class MarkdownWriter:
    """Write chat data to LLM-optimized Markdown format."""

    def __init__(
        self,
        include_reactions: bool = True,
        include_attachments: bool = True,
        include_extraction_guide: bool = False,
        timestamp_format: str = "%H:%M",
        date_format: str = "%Y-%m-%d",
    ) -> None:
        """Initialize markdown writer.

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

    def write(self, chat: Chat, destination: Path) -> None:
        """Write entire chat to markdown file.

        Args:
            chat: Chat entity to write.
            destination: Path to output file.
        """
        content = self._format_chat(chat)
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
            metadata: Optional metadata to include in header.
        """
        lines: list[str] = []

        if metadata:
            lines.append(self._format_metadata(metadata))
            lines.append("")

        lines.extend(self._format_messages(messages))

        content = "\n".join(lines)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def format_to_string(self, chat: Chat) -> str:
        """Format chat to string without writing to file.

        Args:
            chat: Chat entity to format.

        Returns:
            Formatted markdown string.
        """
        return self._format_chat(chat)

    def _format_chat(self, chat: Chat) -> str:
        """Format entire chat to markdown."""
        lines: list[str] = []

        # Header
        lines.append(f"# Chat: {chat.name}")
        lines.append("")

        # Metadata
        if chat.date_range:
            start, end = chat.date_range
            lines.append(
                f"**Period:** {start.strftime(self._date_format)} — "
                f"{end.strftime(self._date_format)}"
            )

        if chat.participants:
            names = sorted(p.name for p in chat.participants.values())[:10]
            lines.append(f"**Participants:** {', '.join(names)}")
            if len(chat.participants) > 10:
                lines.append(f"  *(and {len(chat.participants) - 10} more)*")

        lines.append(f"**Messages:** {len(chat.messages)}")

        if chat.topics:
            lines.append(f"**Topics:** {len(chat.topics)}")

        lines.append("")
        lines.append("---")
        lines.append("")

        # Messages grouped by date
        lines.extend(self._format_messages(chat.messages))

        # Extraction guide
        if self._include_extraction_guide:
            from tg_parser.domain.constants import EXTRACTION_GUIDE_RU

            lines.append(EXTRACTION_GUIDE_RU)

        return "\n".join(lines)

    def _format_messages(self, messages: list[Message]) -> list[str]:
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

            # Message
            lines.extend(self._format_message(msg))
            lines.append("")

        return lines

    def _format_message(self, msg: Message) -> list[str]:
        """Format single message."""
        lines: list[str] = []

        # Header: time + author
        time_str = msg.timestamp.strftime(self._timestamp_format)
        lines.append(f"### {time_str} — {msg.author_name}")

        # Reply quote
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

        # Main text
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

    def _format_metadata(self, metadata: dict[str, Any]) -> str:
        """Format metadata header."""
        lines: list[str] = []

        for key, value in metadata.items():
            lines.append(f"**{key}:** {value}")

        return "\n".join(lines)
