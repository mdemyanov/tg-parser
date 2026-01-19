"""Chunker protocol for splitting messages into LLM-friendly chunks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message


class ChunkerProtocol(Protocol):
    """Protocol for chunking strategies."""

    def chunk(
        self,
        messages: list[Message],
        max_tokens: int,
        **options: Any,
    ) -> list[list[Message]]:
        """Split messages into chunks respecting token limits.

        Args:
            messages: List of messages to chunk.
            max_tokens: Maximum tokens per chunk.
            **options: Strategy-specific options.

        Returns:
            List of message chunks.
        """
        ...
