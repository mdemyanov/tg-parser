"""Parse chat use case."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from tg_parser.domain.entities.chat import Chat
from tg_parser.infrastructure.filters.composite import build_filter
from tg_parser.infrastructure.readers import TelegramJSONReader, get_reader

if TYPE_CHECKING:
    from tg_parser.domain.value_objects.filter_spec import FilterSpecification


class ParseChatUseCase:
    """Use case for parsing Telegram JSON exports."""

    def __init__(
        self,
        reader: TelegramJSONReader | None = None,
        streaming: bool | None = None,
    ) -> None:
        """Initialize with optional custom reader.

        Args:
            reader: Custom reader implementation. If None, uses default.
            streaming: Force streaming mode. None = auto-detect based on file size.
                Only used when reader is None.
        """
        self._reader = reader
        self._streaming = streaming

    def execute(
        self,
        source: Path,
        filter_spec: FilterSpecification | None = None,
    ) -> Chat:
        """Parse chat from source with optional filtering.

        Args:
            source: Path to result.json export file.
            filter_spec: Optional filter specification.

        Returns:
            Chat entity with (filtered) messages.

        Raises:
            FileNotFoundError: If source doesn't exist.
            InvalidExportError: If JSON format is invalid.
        """
        # Get reader (use injected or select based on file size)
        reader = self._reader or get_reader(source, streaming=self._streaming)

        # Read raw chat
        chat = reader.read(source)

        # Apply filters if specified
        if filter_spec and not filter_spec.is_empty():
            filter_func = build_filter(filter_spec, topics_map=chat.topics)
            chat.messages = list(filter_func.filter(chat.messages))

        return chat
