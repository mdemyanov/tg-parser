"""Writer protocols for chat output formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from tg_parser.domain.entities.chat import Chat
    from tg_parser.domain.entities.message import Message


class ChatWriterProtocol(Protocol):
    """Protocol for writing chat data to various formats."""

    def write(self, chat: Chat, destination: Path) -> None:
        """Write entire chat to destination file.

        Args:
            chat: Chat entity to write.
            destination: Path to output file.

        Raises:
            WriterError: If writing fails.
        """
        ...

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

        Raises:
            WriterError: If writing fails.
        """
        ...
