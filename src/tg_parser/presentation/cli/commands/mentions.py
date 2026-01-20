"""Mentions command for CLI."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import typer
from rich.table import Table

from tg_parser.application.use_cases.get_mentions import (
    GetMentionsUseCase,
    MentionsResult,
)
from tg_parser.application.use_cases.parse_chat import ParseChatUseCase
from tg_parser.domain.value_objects.date_range import DateRange
from tg_parser.domain.value_objects.filter_spec import FilterSpecification
from tg_parser.presentation.cli.app import app, console, get_config


@app.command()
def mentions(
    input_path: Path = typer.Argument(
        ...,
        help="Path to Telegram JSON export.",
        exists=True,
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
    topics: str | None = typer.Option(
        None,
        "--topics",
        help="Filter by topic names (comma-separated, partial match).",
    ),
    min_count: int | None = typer.Option(
        None,
        "--min-count",
        "-m",
        help="Minimum mention count to show (default: from config).",
    ),
    output_format: str | None = typer.Option(
        None,
        "-f",
        "--format",
        help="Output format: table or json (default: from config).",
    ),
) -> None:
    """Show mentioned users analysis."""
    # Resolve defaults from config
    config = get_config()
    if min_count is None:
        min_count = config.mentions.min_count
    if output_format is None:
        output_format = config.mentions.output_format

    # Build filter spec
    date_range = _build_date_range(date_from, date_to, last_days)
    topic_set = (
        frozenset(t.strip() for t in topics.split(",") if t.strip())
        if topics
        else frozenset()
    )

    filter_spec = FilterSpecification(
        date_range=date_range,
        topics=topic_set,
    )

    # Parse chat with filters
    parse_use_case = ParseChatUseCase()
    chat = parse_use_case.execute(input_path, filter_spec)

    # Get mentions
    mentions_use_case = GetMentionsUseCase()
    result = mentions_use_case.execute(chat, min_count=min_count)

    if output_format == "json":
        _output_json(result)
    else:
        _output_table(result)


def _build_date_range(
    date_from: str | None,
    date_to: str | None,
    last_days: int | None,
) -> DateRange | None:
    """Build DateRange from CLI options."""
    if last_days:
        return DateRange(
            start=datetime.now() - timedelta(days=last_days),
            end=datetime.now(),
        )
    if date_from or date_to:
        start = datetime.fromisoformat(date_from) if date_from else None
        end = datetime.fromisoformat(date_to) if date_to else None
        return DateRange(start=start, end=end)
    return None


def _output_table(result: MentionsResult) -> None:
    """Output mentions as Rich table."""
    console.print(f"\n[bold]Chat:[/] {result.chat_name}")
    if result.date_range:
        start, end = result.date_range
        console.print(f"[bold]Period:[/] {start.date()} — {end.date()}")
    console.print(f"[bold]Total mentions:[/] {result.total_mentions}")
    console.print(f"[bold]Unique users:[/] {result.unique_users}\n")

    if not result.mentions:
        console.print("[dim]No mentions found.[/]")
        return

    table = Table(title="Mentioned Users")
    table.add_column("#", style="dim", justify="right")
    table.add_column("Mention", style="cyan")
    table.add_column("Count", style="green", justify="right")
    table.add_column("Matched Participant", style="yellow")
    table.add_column("First", style="dim")
    table.add_column("Last", style="dim")

    for i, m in enumerate(result.mentions, 1):
        matched = m.participant_match.name if m.participant_match else "-"
        table.add_row(
            str(i),
            f"@{m.mention}",
            str(m.count),
            matched,
            m.first_mention.strftime("%Y-%m-%d"),
            m.last_mention.strftime("%Y-%m-%d"),
        )

    console.print(table)


def _output_json(result: MentionsResult) -> None:
    """Output mentions as JSON."""
    data = {
        "chat_name": result.chat_name,
        "date_range": {
            "start": result.date_range[0].isoformat() if result.date_range else None,
            "end": result.date_range[1].isoformat() if result.date_range else None,
        },
        "total_mentions": result.total_mentions,
        "unique_users": result.unique_users,
        "mentions": [
            {
                "mention": m.mention,
                "count": m.count,
                "participant_match": {
                    "id": m.participant_match.id,
                    "name": m.participant_match.name,
                    "username": m.participant_match.username,
                }
                if m.participant_match
                else None,
                "first_mention": m.first_mention.isoformat(),
                "last_mention": m.last_mention.isoformat(),
            }
            for m in result.mentions
        ],
    }
    console.print(json.dumps(data, indent=2, ensure_ascii=False))
