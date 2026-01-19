"""Chunk command for CLI."""

from __future__ import annotations

from collections.abc import Callable
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

from tg_parser.application.use_cases.chunk_chat import ChunkChatUseCase
from tg_parser.domain.exceptions import ChunkingError, InvalidExportError
from tg_parser.infrastructure.readers import get_reader, is_ijson_available
from tg_parser.infrastructure.writers.markdown import MarkdownWriter
from tg_parser.presentation.cli.app import app, console

if TYPE_CHECKING:
    from tg_parser.application.use_cases.chunk_chat import ChunkResult

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
def chunk(
    input_path: Path = typer.Argument(
        ...,
        help="Path to Telegram JSON export (result.json).",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    output: Path = typer.Option(
        Path("./chunks"),
        "-o",
        "--output",
        help="Output directory for chunks.",
    ),
    strategy: str = typer.Option(
        "fixed",
        "-s",
        "--strategy",
        help="Chunking strategy: fixed, topic, hybrid.",
    ),
    max_tokens: int = typer.Option(
        8000,
        "-t",
        "--max-tokens",
        help="Maximum tokens per chunk.",
    ),
    single_file: bool = typer.Option(
        False,
        "--single-file",
        help="Output all chunks to a single file with separators.",
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
        help="Verbose output with chunk details.",
    ),
) -> None:
    """Chunk Telegram chat export for LLM processing.

    Splits messages into chunks using the specified strategy:

    \b
    - fixed: Split by token count (default)
    - topic: Split by forum topic
    - hybrid: Split by topic, subdivide large topics by time
    """
    try:
        # Validate strategy
        valid_strategies = {"fixed", "topic", "hybrid"}
        if strategy not in valid_strategies:
            console.print(f"[red]Invalid strategy: {strategy}[/]")
            console.print(f"Valid strategies: {', '.join(sorted(valid_strategies))}")
            raise typer.Exit(1)

        # Determine if we should use streaming with progress
        file_size_mb = input_path.stat().st_size / (1024 * 1024)
        use_streaming = streaming if streaming is not None else (
            file_size_mb > 50 and is_ijson_available()
        )
        show_progress = use_streaming and file_size_mb > PROGRESS_THRESHOLD_MB

        # Execute chunking with or without progress bar
        if show_progress:
            result = _chunk_with_progress(
                input_path, strategy=strategy, max_tokens=max_tokens
            )
        else:
            use_case = ChunkChatUseCase(streaming=use_streaming)
            result = use_case.execute(
                input_path, strategy=strategy, max_tokens=max_tokens
            )

        if not result.chunks:
            console.print("[yellow]No messages to chunk.[/]")
            raise typer.Exit(0)

        # Create output directory
        output.mkdir(parents=True, exist_ok=True)

        # Write chunks
        writer = MarkdownWriter(include_extraction_guide=include_extraction_guide)

        if single_file:
            _write_single_file(result, output, include_extraction_guide)
        else:
            _write_multiple_files(writer, result, output)

        # Success message
        _print_summary(result, output, verbose)

    except typer.Exit:
        # Re-raise typer.Exit without catching
        raise
    except FileNotFoundError as e:
        console.print(f"[red]File not found:[/] {e}")
        raise typer.Exit(1) from e
    except InvalidExportError as e:
        console.print(f"[red]Invalid export:[/] {e.reason}")
        raise typer.Exit(1) from e
    except ChunkingError as e:
        console.print(f"[red]Chunking error:[/] {e}")
        raise typer.Exit(1) from e
    except ImportError as e:
        console.print(f"[red]Missing dependency:[/] {e}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(2) from e


def _chunk_with_progress(
    input_path: Path,
    strategy: str,
    max_tokens: int,
) -> ChunkResult:
    """Chunk with streaming and progress bar.

    Args:
        input_path: Path to JSON export.
        strategy: Chunking strategy.
        max_tokens: Maximum tokens per chunk.

    Returns:
        ChunkResult with chunks.
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

        # Update task description for chunking
        progress.update(task, description="Chunking...")

    # Chunk the parsed chat
    use_case = ChunkChatUseCase()
    return use_case.execute_on_chat(chat, strategy=strategy, max_tokens=max_tokens)


def _write_single_file(
    result: ChunkResult, output: Path, include_extraction_guide: bool = False
) -> None:
    """Write all chunks to a single markdown file."""
    lines: list[str] = []
    lines.append(f"# {result.chat_name} - Chunked Output")
    lines.append("")
    lines.append(f"**Strategy:** {result.strategy}")
    lines.append(f"**Total chunks:** {len(result.chunks)}")
    lines.append(f"**Total messages:** {result.total_messages}")
    lines.append(f"**Estimated tokens:** {result.total_tokens}")
    lines.append("")

    for chunk_obj in result.chunks:
        meta = chunk_obj.metadata
        lines.append("---")
        lines.append("")
        lines.append(f"## Chunk {meta.chunk_index + 1} of {meta.total_chunks}")

        if meta.topic_title:
            if meta.total_parts > 1:
                lines.append(
                    f"**Topic:** {meta.topic_title} "
                    f"(Part {meta.part_number}/{meta.total_parts})"
                )
            else:
                lines.append(f"**Topic:** {meta.topic_title}")

        if meta.date_range_start and meta.date_range_end:
            lines.append(
                f"**Period:** {meta.date_range_start.strftime('%Y-%m-%d %H:%M')} - "
                f"{meta.date_range_end.strftime('%Y-%m-%d %H:%M')}"
            )

        lines.append(f"**Messages:** {chunk_obj.message_count}")
        lines.append(f"**Tokens:** ~{meta.estimated_tokens}")
        lines.append("")

        # Format messages
        for msg in chunk_obj.messages:
            time_str = msg.timestamp.strftime("%Y-%m-%d %H:%M")
            text = msg.text.replace("\n", " ").strip()
            lines.append(f"**[{time_str}] {msg.author_name}:** {text}")
            lines.append("")

    # Extraction guide
    if include_extraction_guide:
        from tg_parser.domain.constants import EXTRACTION_GUIDE_RU

        lines.append(EXTRACTION_GUIDE_RU)

    content = "\n".join(lines)
    output_file = output / "chunks.md"
    output_file.write_text(content, encoding="utf-8")


def _write_multiple_files(
    writer: MarkdownWriter, result: ChunkResult, output: Path
) -> None:
    """Write each chunk to a separate file."""
    for chunk_obj in result.chunks:
        meta = chunk_obj.metadata

        # Generate filename
        if meta.topic_title:
            safe_topic = "".join(
                c if c.isalnum() or c in (" ", "-", "_") else "_"
                for c in meta.topic_title
            )[:30]
            if meta.total_parts > 1:
                filename = (
                    f"chunk_{meta.chunk_index + 1:03d}_{safe_topic}_"
                    f"part{meta.part_number}.md"
                )
            else:
                filename = f"chunk_{meta.chunk_index + 1:03d}_{safe_topic}.md"
        else:
            filename = f"chunk_{meta.chunk_index + 1:03d}.md"

        # Build metadata dict
        metadata: dict[str, str] = {
            "Chunk": f"{meta.chunk_index + 1} of {meta.total_chunks}",
            "Strategy": meta.strategy,
            "Messages": str(chunk_obj.message_count),
            "Estimated tokens": str(meta.estimated_tokens),
        }

        if meta.topic_title:
            if meta.total_parts > 1:
                metadata["Topic"] = (
                    f"{meta.topic_title} (Part {meta.part_number}/{meta.total_parts})"
                )
            else:
                metadata["Topic"] = meta.topic_title

        if meta.date_range_start and meta.date_range_end:
            metadata["Period"] = (
                f"{meta.date_range_start.strftime('%Y-%m-%d %H:%M')} - "
                f"{meta.date_range_end.strftime('%Y-%m-%d %H:%M')}"
            )

        writer.write_messages(
            list(chunk_obj.messages),
            output / filename,
            metadata=metadata,
        )


def _print_summary(result: ChunkResult, output: Path, verbose: bool) -> None:
    """Print chunking summary."""
    console.print(
        Panel(
            f"[green]Created {len(result.chunks)} chunks[/]\n"
            f"Strategy: {result.strategy}\n"
            f"Output: {output}",
            title="Success",
        )
    )

    if verbose:
        table = Table(title="Chunk Details")
        table.add_column("#", style="cyan", width=4)
        table.add_column("Topic", style="green")
        table.add_column("Messages", justify="right")
        table.add_column("Tokens", justify="right")
        table.add_column("Date Range", style="dim")

        for chunk_obj in result.chunks:
            meta = chunk_obj.metadata
            topic_str = meta.topic_title or "-"
            if meta.total_parts > 1:
                topic_str += f" ({meta.part_number}/{meta.total_parts})"

            date_range = "-"
            if meta.date_range_start and meta.date_range_end:
                date_range = (
                    f"{meta.date_range_start.strftime('%m/%d')} - "
                    f"{meta.date_range_end.strftime('%m/%d')}"
                )

            table.add_row(
                str(meta.chunk_index + 1),
                topic_str,
                str(chunk_obj.message_count),
                f"~{meta.estimated_tokens}",
                date_range,
            )

        console.print(table)
