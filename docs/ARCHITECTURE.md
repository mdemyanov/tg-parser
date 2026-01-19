# tg-parser Architecture Guide

## Clean Architecture Layers

```
presentation/  →  application/  →  domain/  ←  infrastructure/
   (CLI, MCP)      (use cases)    (entities)    (adapters)
```

**Dependencies flow inward.** Domain has no external dependencies. Infrastructure implements domain protocols.

## Core Design Principles

### 1. Immutable Domain Entities

All entities and value objects use frozen dataclasses:

```python
@dataclass(frozen=True, slots=True)
class Message:
    id: MessageId
    timestamp: datetime
    author_name: str
    text: str
    # ...
```

**Why:**
- Thread-safe by default
- Prevents accidental mutations
- Enables caching and memoization
- Clearer reasoning about data flow

### 2. Protocol-Based Dependency Injection

Define interfaces as protocols in `domain/protocols/`:

```python
# domain/protocols/filter_protocol.py
from typing import Protocol
from tg_parser.domain.entities import Message

class FilterProtocol(Protocol):
    """Protocol for message filtering strategies."""

    def matches(self, message: Message) -> bool:
        """Check if message matches filter criteria."""
        ...
```

Implement in `infrastructure/`:

```python
# infrastructure/filters/date_filter.py
from tg_parser.domain.protocols import FilterProtocol
from tg_parser.domain.entities import Message

class DateFilter(FilterProtocol):
    def __init__(self, start: datetime | None, end: datetime | None) -> None:
        self._start = start
        self._end = end

    def matches(self, message: Message) -> bool:
        if self._start and message.timestamp < self._start:
            return False
        if self._end and message.timestamp > self._end:
            return False
        return True
```

**Why:**
- Testable without concrete implementations
- Easy to swap implementations
- No runtime dependency injection framework needed
- Type-safe duck typing

### 3. Type Safety First

```python
# ✅ DO: Use NewType for domain identifiers
from typing import NewType

MessageId = NewType("MessageId", int)
UserId = NewType("UserId", str)
TopicId = NewType("TopicId", int)

# ✅ DO: Use | None instead of Optional
def get_topic(self, topic_id: TopicId) -> Topic | None:
    return self.topics.get(topic_id)

# ✅ DO: Use modern union syntax
def parse_text(text: str | list | None) -> str:
    ...

# ❌ DON'T: Use Any
def process(data: Any) -> Any:  # BAD!

# ❌ DON'T: Use Dict/List (use lowercase)
def get_messages(self) -> List[Message]:  # BAD!
def get_messages(self) -> list[Message]:  # GOOD!

# ❌ DON'T: Skip type hints
def calculate_tokens(text):  # BAD!
    return len(text) // 4
```

### 4. Explicit Over Implicit

No magic, clear data flow:

```python
# ✅ GOOD: Explicit transformation
def parse_chat(source: Path, filter_spec: FilterSpecification | None = None) -> Chat:
    raw_data = read_json(source)
    messages = parse_messages(raw_data["messages"])
    if filter_spec:
        filter_func = build_filter(filter_spec)
        messages = [m for m in messages if filter_func.matches(m)]
    return Chat(messages=messages, ...)

# ❌ BAD: Hidden magic
@auto_filter  # What does this do?
def parse_chat(source: Path) -> Chat:
    ...
```

### 5. Fail Fast with Context

Raise domain exceptions with actionable messages:

```python
# domain/exceptions.py
class TgParserError(Exception):
    """Base exception for all tg-parser errors."""

class InvalidExportError(TgParserError):
    """Raised when JSON doesn't match expected Telegram format."""

    def __init__(self, path: Path, reason: str):
        self.path = path
        self.reason = reason
        super().__init__(f"Invalid export at {path}: {reason}")

# Usage
if "messages" not in data:
    raise InvalidExportError(source, "Missing 'messages' field")
```

## Domain Model

### Core Entities

#### Message

Single chat message with all metadata:

```python
@dataclass(frozen=True, slots=True)
class Message:
    """Single message in a chat."""

    id: MessageId
    timestamp: datetime
    author_name: str
    author_id: UserId
    text: str
    message_type: MessageType = MessageType.TEXT
    topic_id: TopicId | None = None
    reply_to: ReplyInfo | None = None
    forward_from: str | None = None
    mentions: tuple[str, ...] = ()
    attachments: tuple[Attachment, ...] = ()
    reactions: dict[str, int] = field(default_factory=dict)

    @property
    def has_text(self) -> bool:
        """Check if message has non-empty text."""
        return bool(self.text.strip())

    @property
    def is_service(self) -> bool:
        """Check if message is a service message."""
        return self.message_type == MessageType.SERVICE
```

#### Chat

Aggregate root containing all chat data:

```python
@dataclass(frozen=True, slots=True)
class Chat:
    """Chat aggregate containing messages, topics, and participants."""

    id: int
    name: str
    chat_type: ChatType
    messages: list[Message]
    topics: dict[TopicId, Topic] = field(default_factory=dict)
    participants: dict[UserId, Participant] = field(default_factory=dict)

    def messages_by_topic(self, topic_id: TopicId) -> list[Message]:
        """Get all messages in a specific topic."""
        return [m for m in self.messages if m.topic_id == topic_id]

    def messages_by_author(self, author_id: UserId) -> list[Message]:
        """Get all messages from a specific author."""
        return [m for m in self.messages if m.author_id == author_id]
```

#### Topic

Forum topic entity:

```python
@dataclass(frozen=True, slots=True)
class Topic:
    """Forum topic in supergroup_forum chats."""

    id: TopicId
    title: str
    created_at: datetime | None = None
    is_general: bool = False
```

#### Participant

Chat participant with statistics:

```python
@dataclass(frozen=True, slots=True)
class Participant:
    """Chat participant with message statistics."""

    id: UserId
    name: str
    message_count: int = 0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
```

### Value Objects

#### FilterSpecification

Immutable filter configuration:

```python
@dataclass(frozen=True, slots=True)
class FilterSpecification:
    """Immutable specification for message filtering."""

    date_range: DateRange | None = None
    senders: frozenset[str] = field(default_factory=frozenset)
    exclude_senders: frozenset[str] = field(default_factory=frozenset)
    topics: frozenset[str] = field(default_factory=frozenset)
    exclude_topics: frozenset[str] = field(default_factory=frozenset)
    mentions: frozenset[str] = field(default_factory=frozenset)
    contains_pattern: str | None = None
    min_length: int | None = None
    has_attachment: bool | None = None
    has_reactions: bool | None = None
    exclude_forwards: bool | None = None
    exclude_service: bool = True
```

#### DateRange

Time period value object:

```python
@dataclass(frozen=True, slots=True)
class DateRange:
    """Time period for filtering."""

    start: datetime | None = None
    end: datetime | None = None

    def contains(self, timestamp: datetime) -> bool:
        """Check if timestamp falls within range."""
        if self.start and timestamp < self.start:
            return False
        if self.end and timestamp > self.end:
            return False
        return True
```

### Enums

```python
class ChatType(Enum):
    """Telegram chat type."""
    PERSONAL = "personal"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    SUPERGROUP_FORUM = "supergroup_forum"
    CHANNEL = "channel"

class MessageType(Enum):
    """Message content type."""
    TEXT = "text"
    SERVICE = "service"
    MEDIA = "media"
    STICKER = "sticker"
    VOICE = "voice"
    VIDEO_NOTE = "video_note"

class OutputFormat(Enum):
    """Output format for writers."""
    MARKDOWN = "markdown"
    JSON = "json"
    KB_TEMPLATE = "kb_template"
    CSV = "csv"
```

## Application Layer

### Use Cases

Use cases orchestrate domain operations:

```python
# application/use_cases/parse_chat.py
from pathlib import Path
from tg_parser.domain.entities import Chat
from tg_parser.domain.value_objects import FilterSpecification
from tg_parser.domain.protocols import ReaderProtocol, FilterProtocol
from tg_parser.infrastructure.readers import get_reader
from tg_parser.infrastructure.filters import build_filter

def parse_chat(
    source: Path,
    filter_spec: FilterSpecification | None = None,
    streaming: bool | None = None,
) -> Chat:
    """Parse Telegram JSON export into Chat entity.

    Args:
        source: Path to result.json from Telegram Desktop.
        filter_spec: Optional filtering specification.
        streaming: Force streaming mode. If None, auto-detect based on file size.

    Returns:
        Parsed Chat entity.

    Raises:
        InvalidExportError: If JSON structure invalid.
        FileNotFoundError: If source doesn't exist.
    """
    # Get appropriate reader (standard or streaming)
    reader = get_reader(source, streaming=streaming)

    # Parse chat data
    chat = reader.read(source)

    # Apply filters if specified
    if filter_spec:
        filter_func = build_filter(filter_spec)
        filtered_messages = [m for m in chat.messages if filter_func.matches(m)]
        chat = Chat(
            id=chat.id,
            name=chat.name,
            chat_type=chat.chat_type,
            messages=filtered_messages,
            topics=chat.topics,
            participants=chat.participants,
        )

    return chat
```

## Infrastructure Layer

### Readers

#### TelegramJSONReader

Standard reader for small-medium files:

```python
# infrastructure/readers/telegram_json.py
class TelegramJSONReader:
    """Standard JSON reader for Telegram exports."""

    def read(self, source: Path) -> Chat:
        """Read entire JSON file into memory."""
        data = json.loads(source.read_text(encoding="utf-8"))
        return self._parse_chat(data)
```

#### TelegramStreamReader

Streaming reader for large files (>50MB):

```python
# infrastructure/readers/telegram_stream.py
import ijson

class TelegramStreamReader:
    """Streaming JSON reader using ijson."""

    def read(self, source: Path) -> Chat:
        """Stream messages without loading entire file."""
        with open(source, "rb") as f:
            # Parse metadata
            name = next(ijson.items(f, "name"))
            chat_type = next(ijson.items(f, "type"))

            # Stream messages
            messages = []
            for msg_data in ijson.items(f, "messages.item"):
                messages.append(self._parse_message(msg_data))

        return Chat(messages=messages, ...)
```

### Writers

Writers implement `WriterProtocol`:

```python
# domain/protocols/writer_protocol.py
class WriterProtocol(Protocol):
    """Protocol for output writers."""

    def write(self, chat: Chat, output_path: Path) -> None:
        """Write chat data to output path."""
        ...
```

Implementations:
- **MarkdownWriter** — LLM-optimized markdown
- **JSONWriter** — Structured JSON
- **KBTemplateWriter** — Markdown + YAML frontmatter
- **CSVWriter** (planned) — Tabular format

### Filters

Composite pattern for filters:

```python
# infrastructure/filters/composite.py
class CompositeFilter(FilterProtocol):
    """Combine multiple filters with AND logic."""

    def __init__(self, filters: list[FilterProtocol]) -> None:
        self._filters = filters

    def matches(self, message: Message) -> bool:
        return all(f.matches(message) for f in self._filters)

def build_filter(spec: FilterSpecification) -> FilterProtocol:
    """Build composite filter from specification."""
    filters: list[FilterProtocol] = []

    if spec.date_range:
        filters.append(DateFilter(spec.date_range.start, spec.date_range.end))

    if spec.senders:
        filters.append(SenderFilter(spec.senders, include=True))

    if spec.exclude_service:
        filters.append(ServiceFilter(exclude=True))

    # ... other filters

    return CompositeFilter(filters)
```

### Chunkers

Chunkers split messages for LLM context limits:

```python
# domain/protocols/chunker_protocol.py
class ChunkerProtocol(Protocol):
    """Protocol for message chunking strategies."""

    def chunk(
        self,
        messages: list[Message],
        max_tokens: int,
        **options,
    ) -> list[Chunk]:
        """Split messages into chunks."""
        ...
```

Available strategies:
- **FixedChunker** — Simple token-based splitting
- **TopicChunker** — One chunk per forum topic
- **HybridChunker** — Topic + time-based (recommended)

## Presentation Layer

### CLI

Built with Typer and Rich:

```python
# presentation/cli/app.py
import typer
from rich.console import Console

app = typer.Typer(
    name="tg-parser",
    help="Parse Telegram exports for LLM processing",
    no_args_is_help=True,
)
console = Console()
```

Commands structure:
- `tg-parser parse` — Parse with filters
- `tg-parser stats` — Show statistics
- `tg-parser chunk` — Split for LLM
- `tg-parser mentions` — Analyze mentions

### MCP Server

Model Context Protocol integration:

```python
# presentation/mcp/server.py
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("tg-parser")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        PARSE_TOOL,
        CHUNK_TOOL,
        STATS_TOOL,
        PARTICIPANTS_TOOL,
        TOPICS_TOOL,
        MENTIONS_TOOL,
    ]
```

Available tools:
1. `parse_telegram_export` — Parse with filters
2. `chunk_telegram_export` — Smart chunking
3. `get_chat_statistics` — Chat stats
4. `list_chat_participants` — Participants list
5. `list_chat_topics` — Forum topics
6. `list_mentioned_users` — Mentions analysis

## Testing Strategy

### Test Structure

```
tests/
├── unit/                    # Fast, isolated tests
│   ├── domain/              # Entity/VO logic tests
│   │   ├── entities/
│   │   └── value_objects/
│   ├── application/         # Use case tests
│   └── infrastructure/      # Adapter tests with mocks
│       ├── readers/
│       ├── writers/
│       ├── filters/
│       └── chunkers/
├── integration/             # End-to-end tests
│   ├── test_cli.py
│   └── test_mcp.py
└── fixtures/                # Test data
    ├── personal_chat.json
    ├── supergroup_forum.json
    └── large_export.json
```

### Testing Principles

1. **Unit tests** — Fast, isolated, no I/O
2. **Integration tests** — Real file I/O, CLI invocation
3. **Fixtures** — Real Telegram export samples
4. **Coverage** — Aim for 80%+ (currently 261 tests)

## Performance Considerations

### Memory Management

- Use streaming for files >50MB
- Generators over lists where possible
- Frozen dataclasses with slots for memory efficiency

### Token Counting

SimpleTokenCounter uses ~4 characters per token estimate:

```python
# infrastructure/token_counters/simple_counter.py
class SimpleTokenCounter:
    CHARS_PER_TOKEN = 4

    def count_tokens(self, text: str) -> int:
        return len(text) // self.CHARS_PER_TOKEN
```

For production use with OpenAI models, integrate tiktoken (P2).

## Error Handling

### Exception Hierarchy

```
TgParserError (base)
├── InvalidExportError
├── FilterError
├── ChunkingError
└── WriterError
```

All exceptions provide:
- Clear error message
- Context (file path, reason)
- Actionable guidance

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

## Dependencies

### Production

```toml
[project]
dependencies = [
    "typer>=0.9.0",      # CLI framework
    "rich>=13.0.0",      # Terminal formatting
    "pydantic>=2.0.0",   # Data validation
]

[project.optional-dependencies]
mcp = ["mcp>=1.0.0"]           # MCP server support
tiktoken = ["tiktoken>=0.5.0"]  # Accurate token counting
streaming = ["ijson>=3.2.0"]    # Large file support
```

### Development

```toml
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "pyright>=1.1.0",
]
```

## Future Considerations

### Potential Improvements

1. **Async I/O** — For MCP server performance
2. **Caching** — Memoize parsed chats
3. **Plugin system** — Custom filters/chunkers
4. **Metrics** — Track parsing performance
5. **Internationalization** — Multi-language support

### Anti-Patterns to Avoid

1. ❌ Breaking Clean Architecture layers
2. ❌ Mutable domain entities
3. ❌ Global state
4. ❌ Magic decorators
5. ❌ Implicit type conversions
6. ❌ Premature optimization
