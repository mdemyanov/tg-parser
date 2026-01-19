"""Simple token counter using character-based approximation."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message


class SimpleTokenCounter:
    """Simple token counter using character-based approximation.

    Uses ~4 characters per token as approximation, which is reasonable
    for mixed content (English ~4 chars, Russian ~2-3 chars per token).
    """

    # Average characters per token (approximation for mixed content)
    CHARS_PER_TOKEN = 4

    def count(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to count tokens for.

        Returns:
            Estimated token count.
        """
        return len(text) // self.CHARS_PER_TOKEN + 1

    def count_messages(self, messages: list[Message]) -> int:
        """Estimate total tokens for messages.

        Args:
            messages: List of messages to count.

        Returns:
            Estimated total token count.
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
