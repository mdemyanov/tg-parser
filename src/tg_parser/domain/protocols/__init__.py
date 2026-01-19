"""Domain protocols (ports)."""

from __future__ import annotations

from tg_parser.domain.protocols.chunker import ChunkerProtocol
from tg_parser.domain.protocols.filter import FilterProtocol
from tg_parser.domain.protocols.reader import (
    ChatReaderProtocol,
    StreamingReaderProtocol,
)
from tg_parser.domain.protocols.writer import ChatWriterProtocol

__all__ = [
    "ChatReaderProtocol",
    "ChatWriterProtocol",
    "ChunkerProtocol",
    "FilterProtocol",
    "StreamingReaderProtocol",
]
