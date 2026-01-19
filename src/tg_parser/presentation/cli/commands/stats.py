"""Stats command for CLI."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.table import Table

from tg_parser.application.use_cases.get_statistics import GetStatisticsUseCase
from tg_parser.application.use_cases.parse_chat import ParseChatUseCase
from tg_parser.presentation.cli.app import app, console


@app.command()
def stats(
    input_path: Path = typer.Argument(
        ...,
        help="Path to Telegram JSON export.",
        exists=True,
    ),
    top_senders: int = typer.Option(
        10,
        "--top-senders",
        help="Number of top senders to show.",
    ),
) -> None:
    """Show chat statistics."""
    # Parse chat
    parse_use_case = ParseChatUseCase()
    chat = parse_use_case.execute(input_path)

    # Get statistics
    stats_use_case = GetStatisticsUseCase()
    chat_stats = stats_use_case.execute(chat, top_senders_count=top_senders)

    # Main stats table
    table = Table(title=f"Chat: {chat_stats.chat_name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Type", chat_stats.chat_type)
    table.add_row("Messages", str(chat_stats.total_messages))
    table.add_row("Participants", str(chat_stats.participants_count))
    if chat_stats.date_range:
        start, end = chat_stats.date_range
        table.add_row("Period", f"{start.date()} — {end.date()}")
    table.add_row("Est. Tokens", f"~{chat_stats.estimated_tokens:,}")

    console.print(table)

    # Top senders
    if chat_stats.top_senders:
        console.print()
        sender_table = Table(title="Top Senders")
        sender_table.add_column("#", style="dim")
        sender_table.add_column("Name")
        sender_table.add_column("Messages", justify="right")

        for i, (name, count) in enumerate(chat_stats.top_senders, 1):
            pct = count / chat_stats.total_messages * 100
            sender_table.add_row(str(i), name, f"{count} ({pct:.1f}%)")

        console.print(sender_table)

    # Topics
    if chat_stats.messages_by_topic:
        console.print()
        topic_table = Table(title="Topics")
        topic_table.add_column("Topic")
        topic_table.add_column("Messages", justify="right")

        for topic, count in sorted(
            chat_stats.messages_by_topic.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            topic_table.add_row(topic, str(count))

        console.print(topic_table)
