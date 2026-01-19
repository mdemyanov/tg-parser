"""Reader protocols for chat data sources."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from tg_parser.domain.entities.chat import Chat
    from tg_parser.domain.entities.message import Message


class ChatReaderProtocol(Protocol):
    """Protocol for reading chat data from various sources."""

    def read(self, source: Path) -> Chat:
        """Read entire chat into memory.

        Args:
            source: Path to the chat export file.

        Returns:
            Chat entity with all messages, topics, and participants.

        Raises:
            InvalidExportError: If source format is invalid.
            FileNotFoundError: If source file doesn't exist.
        """
        ...

    def validate(self, source: Path) -> list[str]:
        """Validate source format and return list of warnings.

        Args:
            source: Path to the chat export file.

        Returns:
            List of warning messages (empty if valid).
        """
        ...


class StreamingReaderProtocol(Protocol):
    """Protocol for streaming large chat files."""

    def stream_messages(self, source: Path) -> Iterator[Message]:
        """Stream messages without loading entire file into memory.

        Args:
            source: Path to the chat export file.

        Yields:
            Message entities one by one.
        """
        ...
