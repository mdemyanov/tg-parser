"""Parse command for CLI."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
)
from rich.table import Table

from tg_parser.application.use_cases.parse_chat import ParseChatUseCase
from tg_parser.domain.entities.chat import Chat
from tg_parser.domain.exceptions import InvalidExportError
from tg_parser.domain.value_objects.date_range import DateRange
from tg_parser.domain.value_objects.filter_spec import FilterSpecification
from tg_parser.infrastructure.filters import build_filter
from tg_parser.infrastructure.readers import get_reader, is_ijson_available
from tg_parser.infrastructure.writers import get_writer
from tg_parser.presentation.cli.app import app, console, get_config

if TYPE_CHECKING:
    from tg_parser.domain.entities.message import Message
    from tg_parser.domain.protocols.writer import ChatWriterProtocol
    from tg_parser.domain.value_objects.identifiers import TopicId

SUPPORTED_FORMATS = ("markdown", "kb", "json", "csv")

# Threshold for showing progress bar (in MB)
PROGRESS_THRESHOLD_MB = 10


def _create_progress_callback(
    progress: Progress,
    task_id: TaskID,
) -> Callable[[int, int], None]:
    """Create progress callback for streaming reader.

    Args:
        progress: Rich Progress instance.
        task_id: Task ID to update.

    Returns:
        Callback function for progress updates.
    """

    def callback(current: int, total: int) -> None:
        progress.update(task_id, completed=current, total=total or None)

    return callback


@app.command()
def parse(
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
        help="Output directory (default: ./output or from config).",
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
    date_from: str | None = typer.Option(
        None,
        "--date-from",
        help="Start date (YYYY-MM-DD).",
    ),
    date_to: str | None = typer.Option(
        None,
        "--date-to",
        help="End date (YYYY-MM-DD).",
    ),
    last_days: int | None = typer.Option(
        None,
        "--last-days",
        help="Filter to last N days.",
    ),
    senders: str | None = typer.Option(
        None,
        "--senders",
        help="Filter by sender names (comma-separated).",
    ),
    exclude_senders: str | None = typer.Option(
        None,
        "--exclude-senders",
        help="Exclude sender names (comma-separated).",
    ),
    topics: str | None = typer.Option(
        None,
        "--topics",
        help="Filter by topic names (comma-separated, partial match).",
    ),
    exclude_topics: str | None = typer.Option(
        None,
        "--exclude-topics",
        help="Exclude topic names (comma-separated, partial match).",
    ),
    split_topics: bool = typer.Option(
        False,
        "--split-topics",
        help="Output separate file per topic.",
    ),
    contains: str | None = typer.Option(
        None,
        "--contains",
        help="Filter by content pattern (regex).",
    ),
    include_service: bool = typer.Option(
        False,
        "--include-service",
        help="Include service messages (overrides config exclude_service).",
    ),
    exclude_forwards: bool = typer.Option(
        False,
        "--exclude-forwards",
        help="Exclude forwarded messages.",
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
        help="Verbose output.",
    ),
) -> None:
    """Parse Telegram JSON export with optional filters."""
    try:
        # Resolve defaults from config
        config = get_config()
        if output is None:
            output = config.default.output_dir or Path("./output")
        if output_format is None:
            output_format = config.default.output_format
        # Boolean flags: CLI flags override config when explicitly set
        # no_frontmatter: use config default only if not set via CLI
        if not no_frontmatter:
            no_frontmatter = config.output_markdown.no_frontmatter
        # include_service: if not set, respect config's exclude_service
        if not include_service:
            include_service = not config.filtering.exclude_service
        # exclude_forwards: if not set, use config
        if not exclude_forwards:
            exclude_forwards = config.filtering.exclude_forwards
        # include_extraction_guide: if not set, use config
        if not include_extraction_guide:
            include_extraction_guide = config.output_markdown.include_extraction_guide

        # Validate format
        if output_format not in SUPPORTED_FORMATS:
            console.print(
                f"[red]Unsupported format: {output_format}[/]\n"
                f"Available formats: {', '.join(SUPPORTED_FORMATS)}"
            )
            raise typer.Exit(1)

        # Build filter specification
        filter_spec = _build_filter_spec(
            date_from=date_from,
            date_to=date_to,
            last_days=last_days,
            senders=senders,
            exclude_senders=exclude_senders,
            topics=topics,
            exclude_topics=exclude_topics,
            contains=contains,
            include_service=include_service,
            exclude_forwards=exclude_forwards,
        )

        # Determine if we should use streaming with progress
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        use_streaming = (
            streaming
            if streaming is not None
            else (file_size_mb > 50 and is_ijson_available())
        )
        show_progress = use_streaming and file_size_mb > PROGRESS_THRESHOLD_MB

        # Execute parsing
        chat: Chat
        if show_progress:
            chat = _parse_with_progress(input_path, filter_spec)
        elif use_streaming:
            chat = _parse_streaming(input_path, filter_spec)
        else:
            use_case = ParseChatUseCase()
            chat = use_case.execute(input_path, filter_spec)

        # Write output
        output.mkdir(parents=True, exist_ok=True)

        if split_topics:
            # Split output by topics
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
            msg = f"[green]Split {total_messages} messages into {files_count} files[/]"
            console.print(Panel(f"{msg}\nOutput directory: {output}", title="Success"))
            if verbose:
                table = Table(title="Files Created")
                table.add_column("File", style="cyan")
                table.add_column("Messages", style="green", justify="right")
                for filename, count in sorted(written_files.items()):
                    table.add_row(filename, str(count))
                console.print(table)
        else:
            # Single file output
            _write_single_file(
                chat=chat,
                output=output,
                output_format=output_format,
                no_frontmatter=no_frontmatter,
                include_extraction_guide=include_extraction_guide,
                verbose=verbose,
            )

    except FileNotFoundError as e:
        console.print(f"[red]File not found:[/] {e}")
        raise typer.Exit(1) from e
    except InvalidExportError as e:
        console.print(f"[red]Invalid export:[/] {e.reason}")
        console.print(f"Path: {e.path}")
        raise typer.Exit(1) from e
    except ImportError as e:
        console.print(f"[red]Missing dependency:[/] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(2) from e


def _parse_with_progress(
    input_path: Path,
    filter_spec: FilterSpecification,
) -> Chat:
    """Parse with streaming and progress bar.

    Args:
        input_path: Path to JSON export.
        filter_spec: Filter specification.

    Returns:
        Parsed and filtered Chat.
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("{task.completed}/{task.total} messages"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing...", total=None)

        reader = get_reader(
            input_path,
            streaming=True,
            progress_callback=_create_progress_callback(progress, task),
        )
        chat = reader.read(input_path)

    # Apply filters after reading
    return _apply_filters(chat, filter_spec)


def _parse_streaming(
    input_path: Path,
    filter_spec: FilterSpecification,
) -> Chat:
    """Parse with streaming (no progress bar).

    Args:
        input_path: Path to JSON export.
        filter_spec: Filter specification.

    Returns:
        Parsed and filtered Chat.
    """
    reader = get_reader(input_path, streaming=True)
    chat = reader.read(input_path)
    return _apply_filters(chat, filter_spec)


def _apply_filters(chat: Chat, filter_spec: FilterSpecification) -> Chat:
    """Apply filters to parsed chat.

    Args:
        chat: Parsed chat.
        filter_spec: Filter specification.

    Returns:
        Filtered chat (same instance with filtered messages).
    """
    if filter_spec and not filter_spec.is_empty():
        filter_func = build_filter(filter_spec, topics_map=chat.topics)
        chat.messages = list(filter_func.filter(chat.messages))
    return chat


def _build_filter_spec(
    date_from: str | None,
    date_to: str | None,
    last_days: int | None,
    senders: str | None,
    exclude_senders: str | None,
    topics: str | None,
    exclude_topics: str | None,
    contains: str | None,
    include_service: bool,
    exclude_forwards: bool,
) -> FilterSpecification:
    """Build FilterSpecification from CLI options."""
    # Date range
    date_range: DateRange | None = None
    if last_days:
        date_range = DateRange(
            start=datetime.now() - timedelta(days=last_days),
            end=datetime.now(),
        )
    elif date_from or date_to:
        start = datetime.fromisoformat(date_from) if date_from else None
        end = datetime.fromisoformat(date_to) if date_to else None
        date_range = DateRange(start=start, end=end)

    # Senders
    sender_set = (
        frozenset(s.strip() for s in senders.split(",") if s.strip())
        if senders
        else frozenset()
    )

    exclude_sender_set = (
        frozenset(s.strip() for s in exclude_senders.split(",") if s.strip())
        if exclude_senders
        else frozenset()
    )

    # Topics
    topic_set = (
        frozenset(t.strip() for t in topics.split(",") if t.strip())
        if topics
        else frozenset()
    )

    exclude_topic_set = (
        frozenset(t.strip() for t in exclude_topics.split(",") if t.strip())
        if exclude_topics
        else frozenset()
    )

    # Content pattern
    content_pattern = re.compile(contains, re.IGNORECASE) if contains else None

    return FilterSpecification(
        date_range=date_range,
        senders=sender_set,
        exclude_senders=exclude_sender_set,
        topics=topic_set,
        exclude_topics=exclude_topic_set,
        content_pattern=content_pattern,
        exclude_service=not include_service,
        exclude_forwards=exclude_forwards,
    )


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


def _write_single_file(
    chat: Chat,
    output: Path,
    output_format: str,
    no_frontmatter: bool,
    include_extraction_guide: bool,
    verbose: bool,
) -> None:
    """Write chat to a single output file.

    Args:
        chat: Chat to write.
        output: Output directory.
        output_format: Output format.
        no_frontmatter: Whether to exclude frontmatter.
        include_extraction_guide: Whether to include extraction guide.
        verbose: Whether to show verbose output.
    """
    # Sanitize filename
    safe_name = _sanitize_filename(chat.name)

    # Get writer and extension
    writer = _get_writer_for_format(
        output_format, no_frontmatter, include_extraction_guide
    )
    ext = _get_file_extension(output_format)

    output_file = output / f"{safe_name}{ext}"
    writer.write(chat, output_file)

    # Success message
    console.print(
        Panel(
            f"[green]Parsed {len(chat.messages)} messages[/]\nOutput: {output_file}",
            title="Success",
        )
    )

    if verbose:
        console.print(f"Chat type: {chat.chat_type.value}")
        console.print(f"Participants: {len(chat.participants)}")
        if chat.topics:
            console.print(f"Topics: {len(chat.topics)}")


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
