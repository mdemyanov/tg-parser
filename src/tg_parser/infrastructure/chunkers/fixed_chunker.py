"""Fixed token-based chunker."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tg_parser.infrastructure.token_counters.simple_counter import SimpleTokenCounter

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message


class FixedChunker:
    """Chunk messages by fixed token limit.

    Splits messages into chunks where each chunk's estimated
    token count does not exceed max_tokens. Messages are kept
    in their original order.
    """

    def __init__(self, token_counter: SimpleTokenCounter | None = None) -> None:
        """Initialize with optional custom token counter.

        Args:
            token_counter: Token counter to use. If None, uses default.
        """
        self._counter = token_counter or SimpleTokenCounter()

    def chunk(
        self,
        messages: list[Message],
        max_tokens: int,
        **options: Any,  # noqa: ARG002
    ) -> list[list[Message]]:
        """Split messages into fixed-size chunks by token count.

        Args:
            messages: Messages to chunk.
            max_tokens: Maximum tokens per chunk.
            **options: Unused, for protocol compatibility.

        Returns:
            List of message chunks, each containing a list of messages.
        """
        if not messages:
            return []

        chunks: list[list[Message]] = []
        current_chunk: list[Message] = []
        current_tokens = 0

        for msg in messages:
            msg_tokens = self._counter.count_messages([msg])

            # Start new chunk if adding this message exceeds limit
            # But only if current chunk is not empty (allows single large messages)
            if current_tokens + msg_tokens > max_tokens and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_tokens = 0

            current_chunk.append(msg)
            current_tokens += msg_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks
