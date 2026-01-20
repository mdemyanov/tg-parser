"""Config commands for CLI."""

from __future__ import annotations

import os
from pathlib import Path

import typer
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from tg_parser.domain.exceptions import ConfigError
from tg_parser.infrastructure.config.config_loader import ConfigLoader
from tg_parser.presentation.cli.app import app, console

config_app = typer.Typer(
    name="config",
    help="Manage tg-parser configuration.",
    no_args_is_help=True,
)

# Register as subcommand group
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    config_path: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file (default: auto-discover).",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Show all settings including defaults.",
    ),
) -> None:
    """Show current effective configuration."""
    try:
        loader = ConfigLoader()
        settings = loader.load(config_path)

        # Config source info
        if settings.config_source:
            console.print(f"[dim]Config file:[/] {settings.config_source}")
        else:
            console.print("[dim]Config file:[/] None (using defaults)")
        console.print()

        # Settings table
        table = Table(title="Effective Configuration")
        table.add_column("Section", style="cyan")
        table.add_column("Setting", style="green")
        table.add_column("Value")

        # Default section
        table.add_row("default", "output_format", settings.default.output_format)
        output_dir_str = (
            str(settings.default.output_dir)
            if settings.default.output_dir
            else "(not set)"
        )
        table.add_row("default", "output_dir", output_dir_str)

        if verbose:
            # Filtering section
            table.add_row(
                "filtering", "exclude_service", str(settings.filtering.exclude_service)
            )
            table.add_row(
                "filtering", "exclude_empty", str(settings.filtering.exclude_empty)
            )
            exclude_fwd = str(settings.filtering.exclude_forwards)
            table.add_row("filtering", "exclude_forwards", exclude_fwd)
            table.add_row(
                "filtering",
                "min_message_length",
                str(settings.filtering.min_message_length),
            )

            # Chunking section
            table.add_row("chunking", "strategy", settings.chunking.strategy)
            table.add_row("chunking", "max_tokens", str(settings.chunking.max_tokens))

            # Output.markdown section
            table.add_row(
                "output.markdown",
                "include_extraction_guide",
                str(settings.output_markdown.include_extraction_guide),
            )
            table.add_row(
                "output.markdown",
                "no_frontmatter",
                str(settings.output_markdown.no_frontmatter),
            )

            # Mentions section
            table.add_row("mentions", "min_count", str(settings.mentions.min_count))
            table.add_row("mentions", "output_format", settings.mentions.output_format)

            # Stats section
            table.add_row("stats", "top_senders", str(settings.stats.top_senders))

        console.print(table)

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e.reason}")
        raise typer.Exit(1) from e


@config_app.command("init")
def config_init(
    output: Path = typer.Option(
        Path("./tg-parser.toml"),
        "-o",
        "--output",
        help="Output path for config file.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing file.",
    ),
) -> None:
    """Create an example configuration file."""
    try:
        output = output.expanduser()

        if output.exists() and not force:
            console.print(f"[yellow]File already exists:[/] {output}")
            console.print("Use --force to overwrite.")
            raise typer.Exit(1)

        loader = ConfigLoader()
        example_content = loader.create_example_config()

        # Create parent directories if needed
        output.parent.mkdir(parents=True, exist_ok=True)

        output.write_text(example_content, encoding="utf-8")

        console.print(
            Panel(
                f"[green]Created configuration file at:[/]\n{output}",
                title="Success",
            )
        )

        # Show syntax-highlighted preview
        console.print()
        console.print("[dim]Preview:[/]")
        syntax = Syntax(example_content, "toml", theme="monokai", line_numbers=False)
        console.print(syntax)

    except OSError as e:
        console.print(f"[red]Error writing config file:[/] {e}")
        raise typer.Exit(1) from e


@config_app.command("path")
def config_path() -> None:
    """Show config file search locations."""
    loader = ConfigLoader()

    console.print("[bold]Config file search locations[/] (in priority order):")
    console.print()

    table = Table()
    table.add_column("#", style="dim", width=3)
    table.add_column("Location")
    table.add_column("Status", justify="right")

    # Check TG_PARSER_CONFIG env var
    env_config = os.environ.get(loader.ENV_VAR_NAME)
    if env_config:
        env_path = Path(env_config).expanduser()
        status = "[green]exists[/]" if env_path.exists() else "[dim]not found[/]"
        table.add_row("1", f"$TG_PARSER_CONFIG ({env_path})", status)
        start_index = 2
    else:
        table.add_row("1", "$TG_PARSER_CONFIG [dim](not set)[/]", "[dim]not set[/]")
        start_index = 2

    # Standard locations (skip env var location if already shown)
    locations = loader.get_config_locations()
    # Skip first if it's env var
    if env_config:
        locations = locations[1:]

    for i, location in enumerate(locations, start=start_index):
        status = "[green]exists[/]" if location.exists() else "[dim]not found[/]"
        table.add_row(str(i), str(location), status)

    console.print(table)

    # Show which one would be used
    console.print()
    found = loader.find_config_file()
    if found:
        console.print(f"[bold]Active config:[/] {found}")
    else:
        console.print("[bold]Active config:[/] [dim]None (using built-in defaults)[/]")
