"""Token counters."""

from __future__ import annotations

from typing import Literal

from tg_parser.infrastructure.token_counters.simple_counter import SimpleTokenCounter

# Type alias for token counter types
TokenCounterBackend = Literal["auto", "tiktoken", "simple"]


def get_token_counter(
    backend: TokenCounterBackend = "auto",
) -> SimpleTokenCounter:
    """Get token counter instance by backend preference.

    Args:
        backend: Token counter backend to use:
            - "auto": Use tiktoken if available, otherwise simple (default)
            - "tiktoken": Use tiktoken (raises ImportError if not installed)
            - "simple": Use character-based approximation

    Returns:
        Token counter instance. Type is SimpleTokenCounter for compatibility,
        but may be TiktokenCounter if tiktoken backend is selected.

    Raises:
        ImportError: If tiktoken backend is explicitly requested but not installed.
    """
    if backend == "simple":
        return SimpleTokenCounter()

    if backend == "tiktoken":
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        return TiktokenCounter()  # type: ignore[return-value]

    # auto - try tiktoken, fall back to simple
    try:
        from tg_parser.infrastructure.token_counters.tiktoken_counter import (
            TiktokenCounter,
        )

        return TiktokenCounter()  # type: ignore[return-value]
    except ImportError:
        return SimpleTokenCounter()


__all__ = ["SimpleTokenCounter", "get_token_counter"]
