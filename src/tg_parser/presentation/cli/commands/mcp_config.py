"""MCP configuration command for CLI."""

from __future__ import annotations

import json
from typing import Literal

import typer
from rich.panel import Panel
from rich.syntax import Syntax

from tg_parser.domain.exceptions import ConfigError
from tg_parser.infrastructure.config.mcp_config_manager import MCPConfigManager
from tg_parser.presentation.cli.app import app, console


TargetChoice = Literal["desktop", "code"]


@app.command("mcp-config")
def mcp_config(
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Apply config to Claude Desktop/Code config file.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show what would be written without applying.",
    ),
    no_backup: bool = typer.Option(
        False,
        "--no-backup",
        help="Skip creating backup before modifying.",
    ),
    target: TargetChoice = typer.Option(
        "desktop",
        "--target",
        help="Target application: desktop or code.",
    ),
    use_uv_run: bool = typer.Option(
        False,
        "--use-uv-run",
        help="Use 'uv run' instead of 'uvx' for non-venv installations.",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Verbose output.",
    ),
) -> None:
    """Generate or apply MCP configuration for Claude Desktop/Code.

    By default, prints the JSON configuration to stdout.
    Use --apply to write the configuration to the appropriate config file.

    \b
    Examples:
        # Show config for Claude Desktop
        tg-parser mcp-config

        # Apply config to Claude Desktop
        tg-parser mcp-config --apply

        # Show what would be applied (dry run)
        tg-parser mcp-config --apply --dry-run

        # Apply to Claude Code instead
        tg-parser mcp-config --apply --target code

        # Use 'uv run' instead of 'uvx'
        tg-parser mcp-config --use-uv-run
    """
    try:
        # Initialize manager
        manager = MCPConfigManager(target=target)

        if apply or dry_run:
            _handle_apply(
                manager=manager,
                dry_run=dry_run,
                no_backup=no_backup,
                use_uv_run=use_uv_run,
                verbose=verbose,
            )
        else:
            _handle_print(
                manager=manager,
                use_uv_run=use_uv_run,
                verbose=verbose,
            )

    except ConfigError as e:
        console.print(f"[red]Configuration error:[/] {e.reason}")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error:[/] {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(2) from e


def _handle_print(
    manager: MCPConfigManager,
    use_uv_run: bool,
    verbose: bool,
) -> None:
    """Handle print mode - output config to stdout."""
    config = manager.generate_config(use_uv_run=use_uv_run)
    server_config = manager.get_executable_config(use_uv_run=use_uv_run)

    # Format JSON with pretty printing
    config_json = json.dumps(config, indent=2, ensure_ascii=False)

    if verbose:
        # Show additional info
        env_type = "virtual environment" if manager.is_in_venv() else "system"
        console.print(f"[dim]Environment:[/] {env_type}")
        console.print(f"[dim]Command:[/] {server_config.command}")
        console.print(f"[dim]Args:[/] {' '.join(server_config.args)}")
        console.print()

    # Output syntax-highlighted JSON
    syntax = Syntax(config_json, "json", theme="monokai", line_numbers=False)
    console.print(syntax)

    if verbose:
        console.print()
        console.print(
            "[dim]Copy this configuration to your claude_desktop_config.json[/]"
        )


def _handle_apply(
    manager: MCPConfigManager,
    dry_run: bool,
    no_backup: bool,
    use_uv_run: bool,
    verbose: bool,
) -> None:
    """Handle apply mode - write config to file."""
    config_path = manager.get_config_path()

    if dry_run:
        console.print("[yellow]Dry run mode - no changes will be made[/]")
        console.print()

    # Show what will be written
    config = manager.generate_config(use_uv_run=use_uv_run)
    config_json = json.dumps(config, indent=2, ensure_ascii=False)

    if verbose:
        env_type = "virtual environment" if manager.is_in_venv() else "system"
        console.print(f"[dim]Environment:[/] {env_type}")
        console.print(f"[dim]Target file:[/] {config_path}")
        console.print()
        console.print("[bold]Configuration to apply:[/]")
        syntax = Syntax(config_json, "json", theme="monokai", line_numbers=False)
        console.print(syntax)
        console.print()

    # Apply configuration
    apply_result = manager.apply_config(
        dry_run=dry_run,
        create_backup=not no_backup,
        use_uv_run=use_uv_run,
    )

    # Show result
    if dry_run:
        action = "Would create" if apply_result.created_new else "Would update"
        console.print(
            Panel(
                f"[yellow]{action} configuration at:[/]\n{apply_result.config_path}",
                title="Dry Run",
            )
        )
    else:
        if apply_result.created_new:
            msg = (
                f"[green]Created new configuration at:[/]\n{apply_result.config_path}"
            )
        elif apply_result.updated_existing:
            msg = (
                f"[green]Updated tg-parser entry in:[/]\n{apply_result.config_path}"
            )
        else:
            msg = f"[green]Added tg-parser to:[/]\n{apply_result.config_path}"

        if apply_result.backup_path:
            msg += f"\n\n[dim]Backup created at:[/]\n{apply_result.backup_path}"

        console.print(Panel(msg, title="Success"))

        # Reminder
        console.print()
        console.print("[dim]Restart Claude Desktop to load the new configuration.[/]")
