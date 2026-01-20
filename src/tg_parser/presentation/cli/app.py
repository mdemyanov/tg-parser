"""CLI application using Typer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

if TYPE_CHECKING:
    from tg_parser.domain.value_objects.config_settings import ConfigSettings

app = typer.Typer(
    name="tg-parser",
    help="Parse Telegram Desktop JSON exports for LLM processing.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()


# State for sharing config across commands
class State:
    """Global state for CLI."""

    config: ConfigSettings | None = None
    config_path: Path | None = None


state = State()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        from tg_parser import __version__

        console.print(f"tg-parser version {__version__}")
        raise typer.Exit()


def config_callback(ctx: typer.Context, value: Path | None) -> Path | None:
    """Load configuration from file.

    This callback runs before any command and loads config into global state.
    """
    if ctx.resilient_parsing:
        return None

    from tg_parser.infrastructure.config.config_loader import ConfigLoader

    state.config_path = value

    try:
        loader = ConfigLoader()
        state.config = loader.load(value)
    except Exception as e:
        console.print(f"[yellow]Warning: Could not load config: {e}[/]")
        # Continue with defaults
        from tg_parser.infrastructure.config.config_reader import (
            FileConfigReader,
            TgParserConfigModel,
        )

        reader = FileConfigReader()
        state.config = reader.to_settings(TgParserConfigModel(), source=None)

    return value


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
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        callback=config_callback,
        is_eager=True,
        help="Path to TOML config file.",
    ),
) -> None:
    """tg-parser: Parse Telegram exports for LLM processing."""
    pass


def get_config() -> ConfigSettings:
    """Get loaded configuration.

    Returns:
        ConfigSettings instance, or defaults if not loaded.
    """
    if state.config is None:
        from tg_parser.infrastructure.config.config_loader import ConfigLoader

        loader = ConfigLoader()
        state.config = loader.load(state.config_path)
    return state.config
