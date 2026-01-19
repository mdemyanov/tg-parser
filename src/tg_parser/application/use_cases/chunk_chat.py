"""Chunk chat use case."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tg_parser.application.use_cases.parse_chat import ParseChatUseCase
from tg_parser.domain.entities.chunk import Chunk, ChunkMetadata
from tg_parser.infrastructure.chunkers import get_chunker
from tg_parser.infrastructure.chunkers.hybrid_chunker import HybridChunker
from tg_parser.infrastructure.token_counters.simple_counter import SimpleTokenCounter

if TYPE_CHECKING:
    from pathlib import Path

    from tg_parser.domain.entities.chat import Chat
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.value_objects.filter_spec import FilterSpecification
    from tg_parser.infrastructure.chunkers.hybrid_chunker import HybridChunkInfo


@dataclass(frozen=True, slots=True)
class ChunkResult:
    """Result of chunking operation.

    Attributes:
        chunks: Tuple of Chunk objects with messages and metadata.
        chat_name: Name of the source chat.
        total_messages: Total number of messages processed.
        total_tokens: Estimated total token count.
        strategy: Chunking strategy used.
    """

    chunks: tuple[Chunk, ...]
    chat_name: str
    total_messages: int
    total_tokens: int
    strategy: str


class ChunkChatUseCase:
    """Use case for chunking parsed chat messages.

    Parses a Telegram export and splits messages into chunks using
    the specified strategy. Returns chunks with rich metadata for
    downstream processing.
    """

    DEFAULT_MAX_TOKENS = 8000

    def __init__(
        self,
        parse_use_case: ParseChatUseCase | None = None,
        token_counter: SimpleTokenCounter | None = None,
        streaming: bool | None = None,
    ) -> None:
        """Initialize with optional dependencies.

        Args:
            parse_use_case: Custom parse use case. If None, uses default.
            token_counter: Custom token counter. If None, uses default.
            streaming: Force streaming mode for reading. None = auto-detect.
        """
        self._parse_use_case = parse_use_case or ParseChatUseCase(streaming=streaming)
        self._token_counter = token_counter or SimpleTokenCounter()

    def execute(
        self,
        source: Path,
        strategy: str = "fixed",
        max_tokens: int | None = None,
        filter_spec: FilterSpecification | None = None,
    ) -> ChunkResult:
        """Parse and chunk a chat export.

        Args:
            source: Path to result.json export file.
            strategy: Chunking strategy ("fixed", "topic", "hybrid").
            max_tokens: Maximum tokens per chunk. Uses DEFAULT_MAX_TOKENS if None.
            filter_spec: Optional filter specification.

        Returns:
            ChunkResult with chunks and metadata.

        Raises:
            FileNotFoundError: If source doesn't exist.
            InvalidExportError: If JSON format is invalid.
            ChunkingError: If chunking strategy is unknown.
        """
        if max_tokens is None:
            max_tokens = self.DEFAULT_MAX_TOKENS

        # Parse chat with optional filtering
        chat = self._parse_use_case.execute(source, filter_spec)

        return self.chunk_chat(chat, strategy, max_tokens)

    def execute_on_chat(
        self,
        chat: Chat,
        strategy: str = "fixed",
        max_tokens: int | None = None,
    ) -> ChunkResult:
        """Alias for chunk_chat for consistency with CLI interface.

        Args:
            chat: Parsed Chat entity.
            strategy: Chunking strategy.
            max_tokens: Maximum tokens per chunk.

        Returns:
            ChunkResult with chunks and metadata.
        """
        return self.chunk_chat(chat, strategy, max_tokens)

    def chunk_chat(
        self,
        chat: Chat,
        strategy: str = "fixed",
        max_tokens: int | None = None,
    ) -> ChunkResult:
        """Chunk an already-parsed chat.

        Args:
            chat: Parsed Chat entity.
            strategy: Chunking strategy.
            max_tokens: Maximum tokens per chunk. Uses DEFAULT_MAX_TOKENS if None.

        Returns:
            ChunkResult with chunks and metadata.

        Raises:
            ChunkingError: If chunking strategy is unknown.
        """
        if max_tokens is None:
            max_tokens = self.DEFAULT_MAX_TOKENS

        if not chat.messages:
            return ChunkResult(
                chunks=(),
                chat_name=chat.name,
                total_messages=0,
                total_tokens=0,
                strategy=strategy,
            )

        # Get appropriate chunker
        chunker = get_chunker(strategy)

        # Chunk messages
        if strategy == "hybrid" and isinstance(chunker, HybridChunker):
            # Use hybrid chunker with full info
            chunk_infos = chunker.chunk_with_info(chat.messages, max_tokens)
            chunks = self._build_chunks_from_hybrid(chunk_infos, chat, strategy)
        else:
            # Standard chunking
            message_lists = chunker.chunk(chat.messages, max_tokens)
            chunks = self._build_chunks(message_lists, chat, strategy)

        total_tokens = self._token_counter.count_messages(chat.messages)

        return ChunkResult(
            chunks=tuple(chunks),
            chat_name=chat.name,
            total_messages=len(chat.messages),
            total_tokens=total_tokens,
            strategy=strategy,
        )

    def _build_chunks(
        self,
        message_lists: list[list[Message]],
        chat: Chat,
        strategy: str,
    ) -> list[Chunk]:
        """Build Chunk objects from message lists.

        Args:
            message_lists: Lists of messages from chunker.
            chat: Source chat for topic info.
            strategy: Chunking strategy name.

        Returns:
            List of Chunk objects with metadata.
        """
        total_chunks = len(message_lists)
        chunks: list[Chunk] = []

        for idx, messages in enumerate(message_lists):
            if not messages:
                continue

            # Determine topic info (for topic strategy)
            topic_id = messages[0].topic_id if strategy == "topic" else None
            topic_title = None
            if topic_id and topic_id in chat.topics:
                topic_title = chat.topics[topic_id].title

            # Calculate date range
            timestamps = [m.timestamp for m in messages]

            metadata = ChunkMetadata(
                chunk_index=idx,
                total_chunks=total_chunks,
                topic_id=topic_id,
                topic_title=topic_title,
                part_number=1,
                total_parts=1,
                date_range_start=min(timestamps),
                date_range_end=max(timestamps),
                strategy=strategy,
                estimated_tokens=self._token_counter.count_messages(messages),
            )

            chunks.append(
                Chunk(
                    messages=tuple(messages),
                    metadata=metadata,
                )
            )

        return chunks

    def _build_chunks_from_hybrid(
        self,
        chunk_infos: list[HybridChunkInfo],
        chat: Chat,
        strategy: str,
    ) -> list[Chunk]:
        """Build Chunk objects from hybrid chunker info.

        Args:
            chunk_infos: List of HybridChunkInfo from hybrid chunker.
            chat: Source chat for topic info.
            strategy: Chunking strategy name.

        Returns:
            List of Chunk objects with metadata.
        """
        total_chunks = len(chunk_infos)
        chunks: list[Chunk] = []

        for idx, info in enumerate(chunk_infos):
            if not info.messages:
                continue

            # Get topic title
            topic_title = None
            if info.topic_id and info.topic_id in chat.topics:
                topic_title = chat.topics[info.topic_id].title

            # Calculate date range
            timestamps = [m.timestamp for m in info.messages]

            metadata = ChunkMetadata(
                chunk_index=idx,
                total_chunks=total_chunks,
                topic_id=info.topic_id,
                topic_title=topic_title,
                part_number=info.part_number,
                total_parts=info.total_parts,
                date_range_start=min(timestamps),
                date_range_end=max(timestamps),
                strategy=strategy,
                estimated_tokens=self._token_counter.count_messages(info.messages),
            )

            chunks.append(
                Chunk(
                    messages=tuple(info.messages),
                    metadata=metadata,
                )
            )

        return chunks
