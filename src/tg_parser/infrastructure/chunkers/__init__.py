"""Chunkers for splitting messages into LLM-friendly chunks."""

from __future__ import annotations

from typing import Literal

from tg_parser.domain.exceptions import ChunkingError
from tg_parser.infrastructure.chunkers.fixed_chunker import FixedChunker
from tg_parser.infrastructure.chunkers.hybrid_chunker import HybridChunker
from tg_parser.infrastructure.chunkers.topic_chunker import TopicChunker

ChunkingStrategy = Literal["fixed", "topic", "hybrid"]

CHUNKER_REGISTRY: dict[str, type[FixedChunker | TopicChunker | HybridChunker]] = {
    "fixed": FixedChunker,
    "topic": TopicChunker,
    "hybrid": HybridChunker,
}


def get_chunker(strategy: str) -> FixedChunker | TopicChunker | HybridChunker:
    """Get chunker instance by strategy name.

    Args:
        strategy: One of "fixed", "topic", "hybrid".

    Returns:
        Chunker instance for the specified strategy.

    Raises:
        ChunkingError: If strategy is unknown.
    """
    if strategy not in CHUNKER_REGISTRY:
        available = ", ".join(sorted(CHUNKER_REGISTRY.keys()))
        msg = f"Unknown chunking strategy: {strategy}. Available: {available}"
        raise ChunkingError(msg)
    return CHUNKER_REGISTRY[strategy]()


__all__ = [
    "ChunkingStrategy",
    "FixedChunker",
    "HybridChunker",
    "TopicChunker",
    "get_chunker",
]
