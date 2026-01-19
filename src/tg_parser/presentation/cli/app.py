"""CLI application using Typer."""

from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="tg-parser",
    help="Parse Telegram Desktop JSON exports for LLM processing.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        from tg_parser import __version__

        console.print(f"tg-parser version {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """tg-parser: Parse Telegram exports for LLM processing."""
    pass
