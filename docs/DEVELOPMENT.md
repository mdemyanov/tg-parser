# Development Guide

This guide covers common development tasks, testing, CLI/MCP development, and best practices.

## Table of Contents

- [Setup](#setup)
- [Common Tasks](#common-tasks)
  - [Adding a Filter](#adding-a-filter)
  - [Adding a Chunking Strategy](#adding-a-chunking-strategy)
  - [Adding an MCP Tool](#adding-an-mcp-tool)
  - [Adding a Writer](#adding-a-writer)
- [Testing](#testing)
- [CLI Development](#cli-development)
- [MCP Development](#mcp-development)
- [Code Style](#code-style)
- [Performance](#performance)

## Setup

```bash
# Clone repository
git clone https://github.com/username/tg-parser
cd tg-parser

# Install with all dependencies
uv sync --all-extras

# Verify installation
uv run tg-parser --help
uv run pytest
uv run pyright
```

## Common Tasks

### Adding a Filter

Filters implement `FilterProtocol` and are composed via `CompositeFilter`.

#### 1. Create Filter Class

```python
# src/tg_parser/infrastructure/filters/reaction_filter.py
from __future__ import annotations

from tg_parser.domain.protocols import FilterProtocol
from tg_parser.domain.entities import Message


class ReactionFilter(FilterProtocol):
    """Filter messages by reaction count."""

    def __init__(self, min_reactions: int = 1) -> None:
        self._min_reactions = min_reactions

    def matches(self, message: Message) -> bool:
        """Check if message has enough reactions."""
        total = sum(message.reactions.values())
        return total >= self._min_reactions
```

#### 2. Register in Composite Filter

```python
# src/tg_parser/infrastructure/filters/composite.py
from tg_parser.infrastructure.filters.reaction_filter import ReactionFilter

def build_filter(spec: FilterSpecification) -> FilterProtocol:
    """Build composite filter from specification."""
    filters: list[FilterProtocol] = []

    # ... existing filters

    if spec.has_reactions:
        filters.append(ReactionFilter(min_reactions=1))

    return CompositeFilter(filters)
```

#### 3. Add to FilterSpecification

```python
# src/tg_parser/domain/value_objects/filter_specification.py
@dataclass(frozen=True, slots=True)
class FilterSpecification:
    # ... existing fields
    has_reactions: bool | None = None
```

#### 4. Add CLI Option

```python
# src/tg_parser/presentation/cli/commands/parse.py
@app.command()
def parse(
    # ... existing options
    has_reactions: bool = typer.Option(
        False,
        "--has-reactions",
        help="Only messages with reactions"
    ),
):
    filter_spec = FilterSpecification(
        # ... existing fields
        has_reactions=has_reactions if has_reactions else None,
    )
```

#### 5. Write Tests

```python
# tests/unit/infrastructure/filters/test_reaction_filter.py
import pytest
from datetime import datetime
from tg_parser.domain.entities import Message, MessageType
from tg_parser.infrastructure.filters import ReactionFilter


class TestReactionFilter:
    def test_matches_with_reactions(self):
        """Should match messages with reactions."""
        msg = Message(
            id=1,
            timestamp=datetime.now(),
            author_name="Test",
            author_id="user1",
            text="Hello",
            reactions={"👍": 2, "❤️": 1},
        )
        filter = ReactionFilter(min_reactions=1)
        assert filter.matches(msg) is True

    def test_rejects_without_reactions(self):
        """Should reject messages without reactions."""
        msg = Message(
            id=1,
            timestamp=datetime.now(),
            author_name="Test",
            author_id="user1",
            text="Hello",
            reactions={},
        )
        filter = ReactionFilter(min_reactions=1)
        assert filter.matches(msg) is False

    def test_respects_min_threshold(self):
        """Should respect minimum reaction threshold."""
        msg = Message(
            id=1,
            timestamp=datetime.now(),
            author_name="Test",
            author_id="user1",
            text="Hello",
            reactions={"👍": 1},
        )
        filter = ReactionFilter(min_reactions=2)
        assert filter.matches(msg) is False
```

### Adding a Chunking Strategy

Chunkers implement `ChunkerProtocol` and return list of `Chunk` objects.

#### 1. Create Chunker Class

```python
# src/tg_parser/infrastructure/chunkers/daily.py
from __future__ import annotations

from datetime import date
from tg_parser.domain.protocols import ChunkerProtocol
from tg_parser.domain.entities import Message, Chunk, ChunkMetadata
from tg_parser.infrastructure.token_counters import SimpleTokenCounter


class DailyChunker(ChunkerProtocol):
    """Chunk messages by calendar day."""

    def __init__(self) -> None:
        self._token_counter = SimpleTokenCounter()

    def chunk(
        self,
        messages: list[Message],
        max_tokens: int,
        **options,
    ) -> list[Chunk]:
        """Split messages into daily chunks."""
        if not messages:
            return []

        # Group by day
        by_day: dict[date, list[Message]] = {}
        for msg in messages:
            day = msg.timestamp.date()
            by_day.setdefault(day, []).append(msg)

        # Create chunks
        chunks = []
        for day, day_messages in sorted(by_day.items()):
            tokens = sum(self._token_counter.count_tokens(m.text) for m in day_messages)

            metadata = ChunkMetadata(
                topic_title=None,
                date_range=(day_messages[0].timestamp, day_messages[-1].timestamp),
                message_count=len(day_messages),
                estimated_tokens=tokens,
            )

            chunks.append(Chunk(messages=day_messages, metadata=metadata))

        return chunks
```

#### 2. Register in Chunker Factory

```python
# src/tg_parser/infrastructure/chunkers/__init__.py
from tg_parser.infrastructure.chunkers.daily import DailyChunker

CHUNKER_REGISTRY = {
    "fixed": FixedChunker,
    "topic": TopicChunker,
    "hybrid": HybridChunker,
    "daily": DailyChunker,  # Add new strategy
}
```

#### 3. Add CLI Support

```python
# src/tg_parser/presentation/cli/commands/chunk.py
@app.command()
def chunk(
    strategy: str = typer.Option(
        "hybrid",
        "-s",
        "--strategy",
        help="Chunking strategy: fixed|topic|hybrid|daily"  # Add to help
    ),
):
    # No code changes needed, factory handles new strategy
```

#### 4. Write Tests

```python
# tests/unit/infrastructure/chunkers/test_daily.py
from datetime import datetime
from tg_parser.domain.entities import Message
from tg_parser.infrastructure.chunkers import DailyChunker


class TestDailyChunker:
    def test_chunks_by_day(self):
        """Should create one chunk per day."""
        messages = [
            Message(
                id=1,
                timestamp=datetime(2025, 1, 15, 10, 0),
                author_name="Alice",
                author_id="user1",
                text="Morning",
            ),
            Message(
                id=2,
                timestamp=datetime(2025, 1, 15, 14, 0),
                author_name="Bob",
                author_id="user2",
                text="Afternoon",
            ),
            Message(
                id=3,
                timestamp=datetime(2025, 1, 16, 10, 0),
                author_name="Alice",
                author_id="user1",
                text="Next day",
            ),
        ]

        chunker = DailyChunker()
        chunks = chunker.chunk(messages, max_tokens=8000)

        assert len(chunks) == 2
        assert len(chunks[0].messages) == 2  # Day 1
        assert len(chunks[1].messages) == 1  # Day 2
```

### Adding an MCP Tool

MCP tools are defined in `presentation/mcp/tools.py` and handled in `server.py`.

#### 1. Define Tool Schema

```python
# src/tg_parser/presentation/mcp/tools.py
from mcp.types import Tool

TG_SEARCH_TOOL = Tool(
    name="search_telegram_export",
    description="Search messages by text pattern (regex)",
    inputSchema={
        "type": "object",
        "properties": {
            "input_path": {
                "type": "string",
                "description": "Path to Telegram JSON export file"
            },
            "pattern": {
                "type": "string",
                "description": "Regular expression pattern to search"
            },
            "case_sensitive": {
                "type": "boolean",
                "default": False,
                "description": "Whether search is case-sensitive"
            },
        },
        "required": ["input_path", "pattern"],
    },
)
```

#### 2. Implement Handler

```python
# src/tg_parser/presentation/mcp/server.py
import re
from pathlib import Path
from mcp.types import TextContent
from tg_parser.application.use_cases import parse_chat


async def _handle_search(args: dict) -> list[TextContent]:
    """Handle search_telegram_export tool."""
    input_path = Path(args["input_path"])
    pattern = args["pattern"]
    case_sensitive = args.get("case_sensitive", False)

    # Parse chat
    chat = parse_chat(input_path)

    # Search messages
    flags = 0 if case_sensitive else re.IGNORECASE
    regex = re.compile(pattern, flags=flags)
    matches = [m for m in chat.messages if regex.search(m.text)]

    # Format results
    if not matches:
        return [TextContent(
            type="text",
            text=f"No messages found matching pattern: {pattern}"
        )]

    output_lines = [f"Found {len(matches)} messages:\n"]
    for msg in matches[:50]:  # Limit to 50
        timestamp = msg.timestamp.strftime("%Y-%m-%d %H:%M")
        output_lines.append(f"[{timestamp}] {msg.author_name}: {msg.text[:100]}")

    return [TextContent(type="text", text="\n".join(output_lines))]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    if name == "search_telegram_export":
        return await _handle_search(arguments)
    # ... existing handlers
```

#### 3. Register Tool

```python
# src/tg_parser/presentation/mcp/server.py
@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        # ... existing tools
        TG_SEARCH_TOOL,
    ]
```

#### 4. Write Integration Test

```python
# tests/integration/test_mcp.py
import pytest
from tg_parser.presentation.mcp.server import _handle_search


@pytest.mark.asyncio
async def test_search_tool(fixture_personal_chat):
    """Test search_telegram_export tool."""
    args = {
        "input_path": str(fixture_personal_chat),
        "pattern": "architecture",
        "case_sensitive": False,
    }

    results = await _handle_search(args)

    assert len(results) == 1
    assert "Found" in results[0].text
```

### Adding a Writer

Writers implement `WriterProtocol` and output chat data in specific formats.

#### 1. Create Writer Class

```python
# src/tg_parser/infrastructure/writers/csv_writer.py
from __future__ import annotations

import csv
from pathlib import Path
from tg_parser.domain.protocols import WriterProtocol
from tg_parser.domain.entities import Chat


class CSVWriter(WriterProtocol):
    """Write chat data to CSV format."""

    def write(self, chat: Chat, output_path: Path) -> None:
        """Write chat to CSV file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                "timestamp",
                "author",
                "text",
                "topic",
                "reactions",
                "has_attachment",
            ])

            # Rows
            for msg in chat.messages:
                topic_title = ""
                if msg.topic_id and msg.topic_id in chat.topics:
                    topic_title = chat.topics[msg.topic_id].title

                reactions_str = ",".join(
                    f"{emoji}:{count}"
                    for emoji, count in msg.reactions.items()
                )

                writer.writerow([
                    msg.timestamp.isoformat(),
                    msg.author_name,
                    msg.text,
                    topic_title,
                    reactions_str,
                    len(msg.attachments) > 0,
                ])
```

#### 2. Register in Writer Factory

```python
# src/tg_parser/infrastructure/writers/__init__.py
from tg_parser.infrastructure.writers.csv_writer import CSVWriter

WRITER_REGISTRY = {
    "markdown": MarkdownWriter,
    "json": JSONWriter,
    "kb_template": KBTemplateWriter,
    "csv": CSVWriter,  # Add new writer
}
```

#### 3. Add OutputFormat Enum Value

```python
# src/tg_parser/domain/entities/enums.py
class OutputFormat(Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    KB_TEMPLATE = "kb_template"
    CSV = "csv"  # Add new format
```

#### 4. Update CLI

```python
# src/tg_parser/presentation/cli/commands/parse.py
@app.command()
def parse(
    format: str = typer.Option(
        "markdown",
        "-f",
        "--format",
        help="Output format: markdown|json|kb_template|csv"  # Add csv
    ),
):
    # No code changes needed, factory handles new writer
```

## Testing

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=tg_parser --cov-report=html

# Specific test file
uv run pytest tests/unit/domain/entities/test_message.py

# Specific test
uv run pytest tests/unit/domain/entities/test_message.py::TestMessage::test_has_text

# Verbose output
uv run pytest -v

# Stop on first failure
uv run pytest -x
```

### Writing Tests

#### Unit Test Example

```python
# tests/unit/domain/entities/test_message.py
import pytest
from datetime import datetime
from tg_parser.domain.entities import Message, MessageType


class TestMessage:
    """Tests for Message entity."""

    def test_has_text_returns_true_for_non_empty(self):
        """Should return True for messages with text."""
        msg = Message(
            id=1,
            timestamp=datetime.now(),
            author_name="Test",
            author_id="user1",
            text="Hello world",
        )
        assert msg.has_text is True

    def test_has_text_returns_false_for_empty(self):
        """Should return False for empty text."""
        msg = Message(
            id=1,
            timestamp=datetime.now(),
            author_name="Test",
            author_id="user1",
            text="",
        )
        assert msg.has_text is False

    def test_is_service_for_service_type(self):
        """Should identify service messages."""
        msg = Message(
            id=1,
            timestamp=datetime.now(),
            author_name="Test",
            author_id="user1",
            text="",
            message_type=MessageType.SERVICE,
        )
        assert msg.is_service is True
```

#### Integration Test Example

```python
# tests/integration/test_cli.py
from pathlib import Path
from typer.testing import CliRunner
from tg_parser.presentation.cli import app

runner = CliRunner()


def test_parse_creates_output(tmp_path: Path, fixture_personal_chat: Path):
    """Should create markdown output file."""
    result = runner.invoke(app, [
        "parse",
        str(fixture_personal_chat),
        "-o", str(tmp_path),
    ])

    assert result.exit_code == 0
    assert (tmp_path / "chat.md").exists()


def test_parse_with_filters(tmp_path: Path, fixture_personal_chat: Path):
    """Should apply date filters correctly."""
    result = runner.invoke(app, [
        "parse",
        str(fixture_personal_chat),
        "--date-from", "2025-01-15",
        "-o", str(tmp_path),
    ])

    assert result.exit_code == 0
    content = (tmp_path / "chat.md").read_text()
    assert "2025-01-14" not in content
```

### Fixtures

Create fixtures in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from pathlib import Path
from datetime import datetime
from tg_parser.domain.entities import Message


@pytest.fixture
def fixture_personal_chat() -> Path:
    """Path to personal chat fixture."""
    return Path(__file__).parent / "fixtures" / "personal_chat.json"


@pytest.fixture
def fixture_forum_chat() -> Path:
    """Path to forum chat fixture."""
    return Path(__file__).parent / "fixtures" / "supergroup_forum.json"


@pytest.fixture
def sample_messages() -> list[Message]:
    """Sample messages for testing."""
    return [
        Message(
            id=1,
            timestamp=datetime(2025, 1, 15, 10, 0),
            author_name="Alice",
            author_id="user1",
            text="Hello",
        ),
        Message(
            id=2,
            timestamp=datetime(2025, 1, 15, 10, 5),
            author_name="Bob",
            author_id="user2",
            text="Hi there",
        ),
    ]
```

## CLI Development

### Using Typer

```python
# src/tg_parser/presentation/cli/app.py
import typer
from rich.console import Console

app = typer.Typer(
    name="tg-parser",
    help="Parse Telegram exports for LLM processing",
    no_args_is_help=True,
)
console = Console()


# src/tg_parser/presentation/cli/commands/parse.py
from pathlib import Path
import typer
from tg_parser.presentation.cli.app import app, console


@app.command()
def parse(
    input_path: Path = typer.Argument(
        ...,
        help="Path to Telegram JSON export",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Path = typer.Option(
        Path("./output"),
        "-o",
        "--output",
        help="Output directory",
    ),
    format: str = typer.Option(
        "markdown",
        "-f",
        "--format",
        help="Output format",
    ),
    verbose: bool = typer.Option(
        False,
        "-v",
        "--verbose",
        help="Verbose output",
    ),
):
    """Parse Telegram JSON export with optional filters."""
    try:
        # Implementation
        console.print(f"[green]✓[/] Parsed {len(messages)} messages")
    except InvalidExportError as e:
        console.print(f"[red]Error:[/] {e.reason}")
        raise typer.Exit(1)
```

### Rich Output Formatting

```python
from rich.table import Table
from rich.panel import Panel
from rich.progress import track


def print_statistics(chat: Chat) -> None:
    """Print chat statistics as table."""
    table = Table(title="Chat Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Messages", str(len(chat.messages)))
    table.add_row("Participants", str(len(chat.participants)))
    table.add_row("Topics", str(len(chat.topics)))

    console.print(table)


def process_with_progress(messages: list[Message]) -> None:
    """Process with progress bar."""
    for msg in track(messages, description="Processing messages..."):
        # Process message
        pass
```

## MCP Development

### Server Setup

```python
# src/tg_parser/presentation/mcp/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("tg-parser")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [PARSE_TOOL, STATS_TOOL, CHUNK_TOOL]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    handlers = {
        "parse_telegram_export": _handle_parse,
        "get_chat_statistics": _handle_stats,
        "chunk_telegram_export": _handle_chunk,
    }
    return await handlers[name](arguments)


async def main():
    """Run MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)
```

### Testing MCP Tools

```python
# tests/integration/test_mcp.py
import pytest
from pathlib import Path
from tg_parser.presentation.mcp.server import _handle_parse


@pytest.mark.asyncio
async def test_parse_tool(fixture_personal_chat: Path):
    """Test parse_telegram_export tool."""
    args = {
        "input_path": str(fixture_personal_chat),
        "output_format": "markdown",
    }

    results = await _handle_parse(args)

    assert len(results) == 1
    assert "messages" in results[0].text.lower()
```

## Code Style

### Naming Conventions

```python
# Modules: snake_case
telegram_json.py
filter_service.py

# Classes: PascalCase
class MessageFilter:
class ConversationChunker:

# Functions/methods: snake_case
def parse_chat(path: Path) -> Chat:
def filter_by_date(messages: list[Message]) -> list[Message]:

# Constants: SCREAMING_SNAKE_CASE
DEFAULT_CHUNK_SIZE = 3000
SERVICE_ACTIONS = frozenset({"invite_members", "remove_members"})

# Private: underscore prefix
def _normalize_text(raw: str) -> str:
class _InternalCache:
```

### Docstrings

Use Google style:

```python
def parse_chat(
    source: Path,
    filter_spec: FilterSpecification | None = None,
) -> Chat:
    """Parse Telegram JSON export into Chat entity.

    Args:
        source: Path to result.json from Telegram Desktop export.
        filter_spec: Optional filtering specification. If None, all messages included.

    Returns:
        Chat entity with parsed messages, topics, and participants.

    Raises:
        InvalidExportError: If JSON structure doesn't match Telegram format.
        FileNotFoundError: If source path doesn't exist.

    Example:
        >>> chat = parse_chat(Path("./export/result.json"))
        >>> print(f"Loaded {len(chat.messages)} messages")
    """
```

### Type Hints

```python
# ✅ DO
def get_messages(self) -> list[Message]:
    return self._messages

def get_topic(self, topic_id: TopicId) -> Topic | None:
    return self.topics.get(topic_id)

# ❌ DON'T
def get_messages(self):  # Missing return type
    return self._messages

def process(data: Any) -> Any:  # Using Any
    return data
```

## Performance

### Memory Management

```python
# ✅ Use generators for large datasets
def filter_messages(
    messages: Iterable[Message],
    spec: FilterSpecification,
) -> Iterator[Message]:
    filter_func = build_filter(spec)
    for msg in messages:
        if filter_func.matches(msg):
            yield msg

# ❌ Avoid materializing large lists
def filter_messages(messages: list[Message]) -> list[Message]:
    return [m for m in messages if ...]  # Loads all into memory
```

### Streaming for Large Files

```python
# Use streaming for files >50MB
from tg_parser.infrastructure.readers import get_reader

# Auto-detect based on file size
reader = get_reader(source)  # Automatically chooses streaming if >50MB

# Force streaming
reader = get_reader(source, streaming=True)
```

### Profiling

```python
# Profile with cProfile
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Code to profile
chat = parse_chat(source)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats("cumulative")
stats.print_stats(20)
```

## Error Handling

### Domain Exceptions

```python
# src/tg_parser/domain/exceptions.py
class TgParserError(Exception):
    """Base exception."""

class InvalidExportError(TgParserError):
    """Invalid JSON structure."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid export at {path}: {reason}")
```

### Error Handling Pattern

```python
try:
    chat = parse_chat(source, filter_spec)
except InvalidExportError as e:
    console.print(f"[red]Invalid export:[/] {e.reason}")
    console.print(f"Path: {e.path}")
    raise typer.Exit(1)
except Exception as e:
    console.print(f"[red]Unexpected error:[/] {e}")
    if verbose:
        console.print_exception()
    raise typer.Exit(2)
```

## Useful Commands

```bash
# Development
uv sync --all-extras         # Install dependencies
uv run tg-parser parse ...   # Run CLI
uv run tg-parser mcp         # Run MCP server

# Quality checks
uv run pytest                          # Run tests
uv run pytest --cov=tg_parser         # With coverage
uv run pyright                         # Type check
uv run ruff check --fix               # Lint
uv run ruff format                     # Format

# Build
uv build                     # Build package
uv publish                   # Publish to PyPI
```
