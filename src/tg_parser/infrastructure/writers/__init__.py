"""Chat writers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tg_parser.infrastructure.writers.json_writer import JSONWriter
from tg_parser.infrastructure.writers.kb_template import KBTemplateWriter
from tg_parser.infrastructure.writers.markdown import MarkdownWriter

if TYPE_CHECKING:
    from tg_parser.domain.protocols.writer import ChatWriterProtocol

WRITER_REGISTRY: dict[str, type[MarkdownWriter | KBTemplateWriter | JSONWriter]] = {
    "markdown": MarkdownWriter,
    "kb": KBTemplateWriter,
    "json": JSONWriter,
}


def get_writer(format_name: str, **kwargs: Any) -> ChatWriterProtocol:
    """Get writer instance by format name.

    Args:
        format_name: Output format name (markdown, kb, json).
        **kwargs: Writer-specific configuration options.

    Returns:
        Writer instance implementing ChatWriterProtocol.

    Raises:
        ValueError: If format name is not recognized.
    """
    if format_name not in WRITER_REGISTRY:
        available = ", ".join(WRITER_REGISTRY.keys())
        raise ValueError(f"Unknown format: {format_name}. Available: {available}")
    return WRITER_REGISTRY[format_name](**kwargs)


__all__ = ["JSONWriter", "KBTemplateWriter", "MarkdownWriter", "get_writer"]
