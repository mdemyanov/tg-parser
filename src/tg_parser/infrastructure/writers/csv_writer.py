"""CSV writer for tabular output."""

from __future__ import annotations

import csv
import json
from io import StringIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tg_parser.domain.entities.chat import Chat
    from tg_parser.domain.entities.message import Message


class CSVWriter:
    """Write chat data to CSV format for tabular analysis.

    Flattens message data into rows suitable for spreadsheets and data tools.
    Complex fields (reactions, attachments, mentions) are JSON-encoded.
    """

    # Column definitions for CSV output
    COLUMNS = (
        "id",
        "timestamp",
        "author_id",
        "author_name",
        "text",
        "message_type",
        "topic_id",
        "reply_to_id",
        "forward_from",
        "mentions",
        "reactions",
        "attachments",
    )

    def __init__(
        self,
        include_header: bool = True,
        delimiter: str = ",",
        include_extraction_guide: bool = False,  # noqa: ARG002
    ) -> None:
        """Initialize CSV writer.

        Args:
            include_header: Whether to include header row.
            delimiter: Field delimiter character.
            include_extraction_guide: Ignored for CSV format (no natural place).
        """
        self._include_header = include_header
        self._delimiter = delimiter
        # Note: include_extraction_guide is accepted but not used for CSV
        # as there's no natural place to include guide text in tabular format

    def write(self, chat: Chat, destination: Path) -> None:
        """Write entire chat to CSV file.

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
        metadata: dict[str, Any] | None = None,  # noqa: ARG002
    ) -> None:
        """Write subset of messages to CSV file.

        Args:
            messages: List of messages to write.
            destination: Path to output file.
            metadata: Optional metadata (ignored for CSV format).
        """
        output = StringIO()
        writer = csv.writer(output, delimiter=self._delimiter)

        if self._include_header:
            writer.writerow(self.COLUMNS)

        for msg in messages:
            writer.writerow(self._format_message_row(msg))

        content = output.getvalue()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")

    def format_to_string(self, chat: Chat) -> str:
        """Format chat to CSV string without writing to file.

        Args:
            chat: Chat entity to format.

        Returns:
            Formatted CSV string.
        """
        output = StringIO()
        writer = csv.writer(output, delimiter=self._delimiter)

        if self._include_header:
            writer.writerow(self.COLUMNS)

        for msg in chat.messages:
            writer.writerow(self._format_message_row(msg))

        return output.getvalue()

    def _format_message_row(self, msg: Message) -> list[str]:
        """Format a message as a CSV row.

        Args:
            msg: Message to format.

        Returns:
            List of string values for CSV row.
        """
        return [
            str(msg.id),
            msg.timestamp.isoformat(),
            str(msg.author_id),
            msg.author_name,
            msg.text,
            msg.message_type.value,
            str(msg.topic_id) if msg.topic_id is not None else "",
            str(msg.reply_to.message_id) if msg.reply_to else "",
            msg.forward_from or "",
            json.dumps(list(msg.mentions), ensure_ascii=False) if msg.mentions else "",
            json.dumps(msg.reactions, ensure_ascii=False) if msg.reactions else "",
            self._format_attachments(msg),
        ]

    def _format_attachments(self, msg: Message) -> str:
        """Format attachments as JSON string.

        Args:
            msg: Message with attachments.

        Returns:
            JSON string of attachment types, or empty string.
        """
        if not msg.attachments:
            return ""

        # Include just the essential info for each attachment
        attachment_data = [
            {
                "type": att.type,
                "file_name": att.file_name,
            }
            for att in msg.attachments
        ]
        return json.dumps(attachment_data, ensure_ascii=False)
