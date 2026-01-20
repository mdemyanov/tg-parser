"""Domain exceptions for tg-parser."""

from __future__ import annotations

from pathlib import Path


class TgParserError(Exception):
    """Base exception for all tg-parser errors."""


class InvalidExportError(TgParserError):
    """Raised when JSON doesn't match expected Telegram format."""

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid export at {path}: {reason}")


class FilterError(TgParserError):
    """Raised when filter specification is invalid."""


class ChunkingError(TgParserError):
    """Raised when chunking fails."""


class WriterError(TgParserError):
    """Raised when writing output fails."""


class StreamingError(TgParserError):
    """Raised when streaming operation fails.

    This typically occurs during incremental JSON parsing
    of large Telegram exports when using ijson.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"Streaming error at {path}: {reason}")


class ConfigError(TgParserError):
    """Raised when configuration operation fails."""

    def __init__(self, operation: str, reason: str) -> None:
        self.operation = operation
        self.reason = reason
        super().__init__(f"Config {operation} failed: {reason}")
