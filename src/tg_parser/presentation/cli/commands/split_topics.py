"""Split-topics command for CLI."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.panel import Panel
from rich.table import Table

from tg_parser.application.use_cases.parse_chat import ParseChatUseCase
from tg_parser.domain.entities.chat import Chat
from tg_parser.infrastructure.readers import get_reader, is_ijson_available
from tg_parser.infrastructure.writers import get_writer
from tg_parser.presentation.cli.app import app, console, get_config

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.protocols.writer import ChatWriterProtocol
    from tg_parser.domain.value_objects.identifiers import TopicId

SUPPORTED_FORMATS = ("markdown", "kb", "json", "csv")


def _sanitize_filename(name: str) -> str:
    """Convert string to safe filename.

    Args:
        name: Original name string.

    Returns:
        Safe filename string.
    """
    # Replace problematic characters
    safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in name)
    # Replace spaces with underscores and collapse multiple underscores
    safe = "_".join(safe.split())
    return safe or "unnamed"


def _get_writer_for_format(
    output_format: str,
    no_frontmatter: bool,
    include_extraction_guide: bool = False,
) -> ChatWriterProtocol:
    """Get appropriate writer for format.

    Args:
        output_format: Output format name.
        no_frontmatter: Whether to exclude frontmatter.
        include_extraction_guide: Whether to include extraction guide.

    Returns:
        Writer instance.
    """
    if output_format == "json":
        return get_writer("json", include_extraction_guide=include_extraction_guide)
    elif output_format == "csv":
        return get_writer("csv", include_extraction_guide=include_extraction_guide)
    elif output_format == "kb" and not no_frontmatter:
        return get_writer("kb", include_extraction_guide=include_extraction_guide)
    else:
        return get_writer("markdown", include_extraction_guide=include_extraction_guide)


def _get_file_extension(output_format: str) -> str:
    """Get file extension for format.

    Args:
        output_format: Output format name.

    Returns:
        File extension with leading dot.
    """
    if output_format == "json":
        return ".json"
    elif output_format == "csv":
        return ".csv"
    else:
        return ".md"


def _split_by_topics(
    chat: Chat,
    output: Path,
    output_format: str,
    no_frontmatter: bool,
    include_extraction_guide: bool = False,
) -> dict[str, int]:
    """Split chat messages by topic and write separate files.

    Args:
        chat: Chat to split.
        output: Output directory.
        output_format: Output format.
        no_frontmatter: Whether to exclude frontmatter.
        include_extraction_guide: Whether to include extraction guide.

    Returns:
        Dict mapping filename to message count.
    """
    # Group messages by topic
    messages_by_topic: dict[TopicId | None, list[Message]] = defaultdict(list)
    for msg in chat.messages:
        messages_by_topic[msg.topic_id].append(msg)

    # Get extension
    ext = _get_file_extension(output_format)

    # Track written files
    written_files: dict[str, int] = {}
    used_names: set[str] = set()

    for topic_id, messages in messages_by_topic.items():
        if topic_id is None:
            base_name = "_no_topic"
        else:
            topic = chat.topics.get(topic_id)
            if topic:
                base_name = _sanitize_filename(topic.title)
            else:
                base_name = f"topic_{topic_id}"

        # Handle name collisions
        final_name = base_name
        counter = 2
        while final_name in used_names:
            final_name = f"{base_name}_{counter}"
            counter += 1
        used_names.add(final_name)

        # Create sub-chat for this topic
        topic_name = f"{chat.name} - {base_name}"
        topic_chat = Chat(
            id=chat.id,
            name=topic_name,
            chat_type=chat.chat_type,
            messages=messages,
            topics={topic_id: chat.topics[topic_id]}
            if topic_id and topic_id in chat.topics
            else {},
            participants=chat.participants,
        )

        # Write file
        output_file = output / f"{final_name}{ext}"
        writer = _get_writer_for_format(
            output_format, no_frontmatter, include_extraction_guide
        )
        writer.write(topic_chat, output_file)

        written_files[final_name + ext] = len(messages)

    return written_files


@app.command(name="split-topics")
def split_topics(
    input_path: Path = typer.Argument(
        ...,
        help="Path to Telegram JSON export (result.json).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output: Path | None = typer.Option(
        None,
        "-o",
        "--output",
        help="Output directory for topic files (default: ./topics).",
    ),
    output_format: str | None = typer.Option(
        None,
        "-f",
        "--format",
        help="Output format: markdown, kb, json, csv (default: from config).",
    ),
    no_frontmatter: bool = typer.Option(
        False,
        "--no-frontmatter",
        help="Exclude YAML frontmatter (kb format only).",
    ),
    include_extraction_guide: bool = typer.Option(
        False,
        "--include-extraction-guide",
        help="Append Russian-language artifact extraction template.",
    ),
    streaming: bool | None = typer.Option(
        None,
        "--streaming/--no-streaming",
        help="Force streaming mode for large files. Default: auto (>50MB).",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Show detailed output with files created.",
    ),
) -> None:
    """Split chat messages by forum topic into separate files.

    Reads a Telegram export and creates one output file per topic.
    Messages without a topic are written to '_no_topic' file.

    Works best with forum/supergroup exports that have topics defined.
    For chats without topics, all messages go to a single '_no_topic' file.
    """
    try:
        # Resolve defaults from config
        config = get_config()
        if output is None:
            output = Path("./topics")
        if output_format is None:
            output_format = config.default.output_format
        if not no_frontmatter:
            no_frontmatter = config.output_markdown.no_frontmatter
        if not include_extraction_guide:
            include_extraction_guide = config.output_markdown.include_extraction_guide

        # Validate format
        if output_format not in SUPPORTED_FORMATS:
            console.print(
                f"[red]Unsupported format: {output_format}[/]\n"
                f"Available formats: {', '.join(SUPPORTED_FORMATS)}"
            )
            raise typer.Exit(1)

        # Determine if we should use streaming
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        use_streaming = (
            streaming
            if streaming is not None
            else (file_size_mb > 50 and is_ijson_available())
        )

        # Parse chat
        if use_streaming:
            reader = get_reader(input_path, streaming=True)
            chat = reader.read(input_path)
        else:
            use_case = ParseChatUseCase()
            chat = use_case.execute(input_path)

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        # Split by topics
        written_files = _split_by_topics(
            chat=chat,
            output=output,
            output_format=output_format,
            no_frontmatter=no_frontmatter,
            include_extraction_guide=include_extraction_guide,
        )

        # Summary
        total_messages = sum(written_files.values())
        files_count = len(written_files)
        topics_count = len(chat.topics) if chat.topics else 0

        msg = f"[green]Split {total_messages} messages into {files_count} files[/]"
        if topics_count > 0:
            msg += f"\n[dim]Found {topics_count} topics in chat[/]"

        console.print(Panel(f"{msg}\nOutput directory: {output}", title="Success"))

        if verbose:
            table = Table(title="Files Created")
            table.add_column("File", style="cyan")
            table.add_column("Messages", style="green", justify="right")
            for filename, count in sorted(written_files.items()):
                table.add_row(filename, str(count))
            console.print(table)

    except FileNotFoundError:
        console.print(f"[red]File not found: {input_path}[/]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")
        raise typer.Exit(1) from None
