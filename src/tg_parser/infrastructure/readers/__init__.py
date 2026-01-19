"""Chat readers.

This module provides readers for parsing Telegram JSON exports.
Use get_reader() to automatically select the appropriate reader
based on file size and available dependencies.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from tg_parser.infrastructure.readers.telegram_json import TelegramJSONReader

if TYPE_CHECKING:
    from tg_parser.infrastructure.readers.telegram_stream import TelegramStreamReader

# Progress callback type: (current_messages, total_estimated)
ProgressCallback = Callable[[int, int], None]


def is_ijson_available() -> bool:
    """Check if ijson is installed.

    Returns:
        True if ijson can be imported.
    """
    try:
        import ijson  # noqa: F401

        return True
    except ImportError:
        return False


def get_reader(
    source: Path,
    streaming: bool | None = None,
    streaming_threshold_mb: int = 50,
    progress_callback: ProgressCallback | None = None,
) -> TelegramJSONReader | TelegramStreamReader:
    """Get appropriate reader based on file size and settings.

    Automatically selects between TelegramJSONReader (fast, loads entire file)
    and TelegramStreamReader (memory-efficient, uses ijson) based on file size.

    Args:
        source: Path to JSON export file.
        streaming: Force streaming mode. None = auto-detect based on file size.
        streaming_threshold_mb: File size threshold for auto-streaming (MB).
            Files larger than this will use streaming reader if ijson available.
        progress_callback: Progress callback for streaming reader.
            Called with (current_messages, total_estimated) during parsing.

    Returns:
        TelegramJSONReader for small files or when streaming disabled.
        TelegramStreamReader for large files when ijson available.

    Raises:
        ImportError: If streaming is forced but ijson not available.

    Example:
        >>> # Auto-detect based on file size
        >>> reader = get_reader(Path("./export.json"))
        >>> chat = reader.read(Path("./export.json"))

        >>> # Force streaming mode
        >>> reader = get_reader(Path("./export.json"), streaming=True)

        >>> # With progress callback
        >>> def on_progress(current, total):
        ...     print(f"{current}/{total}")
        >>> reader = get_reader(
        ...     Path("./large_export.json"),
        ...     streaming=True,
        ...     progress_callback=on_progress,
        ... )
    """
    # Determine if streaming is needed
    use_streaming = streaming

    if use_streaming is None:
        # Auto-detect based on file size
        file_size_mb = source.stat().st_size / (1024 * 1024)
        use_streaming = file_size_mb > streaming_threshold_mb and is_ijson_available()

    if use_streaming:
        if not is_ijson_available():
            msg = (
                "Streaming requires ijson. "
                "Install with: uv pip install 'tg-parser[streaming]'"
            )
            raise ImportError(msg)

        from tg_parser.infrastructure.readers.telegram_stream import (
            TelegramStreamReader,
        )

        return TelegramStreamReader(progress_callback=progress_callback)

    return TelegramJSONReader()


__all__ = [
    "TelegramJSONReader",
    "get_reader",
    "is_ijson_available",
]
