"""Token counter using tiktoken for accurate token estimation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message


class TiktokenCounter:
    """Accurate token counter using tiktoken library.

    Uses cl100k_base encoding (GPT-4, Claude compatible).
    Requires tiktoken package: pip install tiktoken
    """

    def __init__(self, encoding: str = "cl100k_base") -> None:
        """Initialize tiktoken counter.

        Args:
            encoding: Tiktoken encoding name. Default is cl100k_base
                     which is compatible with GPT-4 and similar to Claude.
        """
        import tiktoken

        self._encoding = tiktoken.get_encoding(encoding)

    def count(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for.

        Returns:
            Actual token count.
        """
        return len(self._encoding.encode(text))

    def count_messages(self, messages: list[Message]) -> int:
        """Count total tokens for messages.

        Args:
            messages: List of messages to count.

        Returns:
            Total token count with formatting overhead.
        """
        total = 0
        for msg in messages:
            # Count message text
            total += self.count(msg.text)
            # Add overhead for author name, timestamp, formatting
            total += self.count(msg.author_name) + 10
            # Add overhead for attachments
            total += len(msg.attachments) * 5
            # Add overhead for reactions
            total += len(msg.reactions) * 3

        return total
