"""Entry point for tg-parser CLI."""

from __future__ import annotations

import sys


def main() -> None:
    """Main entry point for tg-parser."""
    # Check for MCP mode
    if len(sys.argv) > 1 and sys.argv[1] == "mcp":
        # Import and run MCP server
        try:
            from tg_parser.presentation.mcp.server import (
                run_mcp_server,  # type: ignore[import-not-found]
            )

            run_mcp_server()
        except ImportError:
            print("MCP support not installed. Install with: uv add tg-parser[mcp]")
            sys.exit(1)
    else:
        # Run CLI
        # Import commands to register them (side effect: registers with app)
        import tg_parser.presentation.cli.commands.chunk
        import tg_parser.presentation.cli.commands.parse
        import tg_parser.presentation.cli.commands.stats  # noqa: F401
        from tg_parser.presentation.cli.app import app

        app()


if __name__ == "__main__":
    main()
