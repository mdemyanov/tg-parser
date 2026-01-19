# tg-parser

[![PyPI version](https://badge.fury.io/py/tg-parser.svg)](https://pypi.org/project/tg-parser/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-261%20passing-green.svg)](https://github.com/mdemyanov/tg-parser)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type Checked](https://img.shields.io/badge/type%20checked-pyright-blue.svg)](https://github.com/microsoft/pyright)

**Parse Telegram Desktop JSON exports for LLM processing.**

Transform messy chat exports into clean, structured data ready for summarization, analysis, and artifact extraction with Claude or other LLMs.

## Features

### Implemented ✅ (v1.0.0)

- 🗂️ **All chat types**: Personal, groups, supergroups, forum topics, channels
- 🔍 **Powerful filtering**: 9 filter types (date, sender, content, topic, attachments, reactions, etc.)
- ✂️ **Smart chunking**: 3 strategies (fixed, topic, hybrid) for LLM context limits
- 🚀 **Streaming**: ijson-based reader for files >50MB with auto-detection
- 📝 **Multiple formats**: Markdown (LLM-optimized), JSON, KB-template with YAML frontmatter
- 🔌 **MCP integration**: 6 tools for Claude Desktop/Code
- 📊 **Statistics**: Message counts, top senders, topics breakdown, mention analysis
- ✅ **Type-safe**: pyright strict mode, 261 comprehensive tests

### Coming Soon 🚧

- 📄 **CSV export**: Tabular output format (P2)
- 🔧 **Config files**: TOML configuration support (P3)
- 🎯 **tiktoken**: Accurate token counting (P2)

## Installation

```bash
# From PyPI (recommended)
pip install tg-parser

# With uv
uv tool install tg-parser

# With all extras (MCP, tiktoken, streaming)
pip install "tg-parser[all]"

# From source
git clone https://github.com/mdemyanov/tg-parser.git
cd tg-parser
uv sync --all-extras
```

## Quick Start

### 1. Export from Telegram Desktop

1. Open Telegram Desktop
2. Go to chat → ⋮ menu → Export chat history
3. Select JSON format, uncheck media if not needed
4. Export

### 2. Parse the export

```bash
# Basic parsing
tg-parser parse ./ChatExport/result.json -o ./output/

# Last 7 days only
tg-parser parse ./export.json --last-days 7

# Filter by sender
tg-parser parse ./export.json --senders "Иван Петров,Мария"

# Split forum by topics
tg-parser parse ./forum_export.json --split-topics

# Chunk for LLM context limits
tg-parser chunk ./export.json -s hybrid --max-tokens 8000

# Analyze mentions
tg-parser mentions ./export.json --format json

# Large files with streaming
tg-parser parse ./massive_export.json --streaming

# Get statistics
tg-parser stats ./export.json
```

### 3. Use with Claude

The output is optimized for LLM processing:

```markdown
# Chat: Команда разработки
**Период:** 2025-01-13 — 2025-01-19  
**Участники:** Иван, Мария, Алексей

---

## 2025-01-15

### 10:30 — Иван Петров
Коллеги, нужно обсудить архитектуру нового модуля.

### 10:35 — Мария Сидорова
@Алексей, подготовь диаграмму к завтра.
```

## CLI Reference

### `tg-parser parse`

Main parsing command with filters.

```bash
tg-parser parse <input> [OPTIONS]

# Date filters
--date-from DATE        # Start date (YYYY-MM-DD)
--date-to DATE          # End date
--last-days N           # Last N days
--last-hours N          # Last N hours

# Sender filters
--senders TEXT          # Include senders (comma-separated)
--exclude-senders TEXT  # Exclude senders

# Topic filters (for forum groups)
--topics TEXT           # Include topics
--exclude-topics TEXT   # Exclude topics

# Content filters
--mentions TEXT         # Messages mentioning users
--contains REGEX        # Search pattern
--min-length N          # Minimum text length

# Type filters
--has-attachment        # Only with attachments
--has-reactions         # Only with reactions
--exclude-forwards      # Exclude forwarded
--include-service       # Include service messages

# Output
-o, --output PATH       # Output directory
-f, --format FORMAT     # markdown|json|csv
--split-topics          # Separate file per topic
```

### `tg-parser chunk`

Split parsed output for LLM context limits.

```bash
tg-parser chunk <input> [OPTIONS]

-s, --strategy STRATEGY  # fixed|conversation|topic|daily
--max-tokens N           # Max tokens per chunk (default: 3000)
--time-gap N             # Minutes gap to split (default: 30)
--preserve-threads       # Don't break reply chains
```

### `tg-parser stats`

Chat statistics overview.

```bash
tg-parser stats <input> [OPTIONS]

--format FORMAT          # table|json|markdown
--top-senders N          # Show top N senders
--by-topic               # Group by topic
--by-day                 # Daily breakdown
```

## MCP Server

Use tg-parser directly in Claude Desktop or Claude Code.

### Setup

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tg-parser": {
      "command": "uvx",
      "args": ["tg-parser", "mcp"]
    }
  }
}
```

### Available Tools

| Tool | Description | Status |
|------|-------------|--------|
| `parse_telegram_export` | Parse JSON export with filters | ✅ |
| `chunk_telegram_export` | Split messages for LLM context | ✅ |
| `get_chat_statistics` | Get chat statistics (JSON) | ✅ |
| `list_chat_participants` | List participants with message counts | ✅ |
| `list_chat_topics` | List forum topics with message counts | ✅ |
| `list_mentioned_users` | Analyze @mentions frequency | ✅ |

### Example Usage in Claude

```
User: Parse my team chat from last week and summarize key decisions

Claude: I'll parse the export and prepare it for analysis.
[Uses parse_telegram_export tool with date_from filter]

Based on the parsed chat, here are the key decisions...
```

## Python API

```python
from tg_parser import parse_chat, ChatFilter
from tg_parser.domain.value_objects import FilterSpecification, DateRange
from datetime import datetime, timedelta

# Simple parsing
chat = parse_chat("./export.json")
print(f"Loaded {len(chat.messages)} messages")

# With filters
filter_spec = FilterSpecification(
    date_range=DateRange(
        start=datetime.now() - timedelta(days=7)
    ),
    senders=frozenset(["Иван Петров"]),
    exclude_service=True,
)
chat = parse_chat("./export.json", filter_spec=filter_spec)

# Access data
for topic in chat.topics.values():
    msgs = chat.messages_by_topic(topic.id)
    print(f"{topic.title}: {len(msgs)} messages")

# Chunking
from tg_parser.application.services.chunker import ConversationChunker

chunker = ConversationChunker(max_tokens=3000)
chunks = chunker.chunk(chat.messages)
```

## Output Formats

### Markdown (default)

Clean, human-readable format optimized for LLM comprehension.

### JSON

Structured format for programmatic processing:

```json
{
  "meta": {
    "chat_name": "Team Chat",
    "chat_type": "supergroup_forum",
    "statistics": {
      "total_messages": 127,
      "tokens_estimate": 15000
    }
  },
  "messages": [
    {
      "id": 1234,
      "timestamp": "2025-01-15T10:30:00Z",
      "author": "Иван Петров",
      "text": "...",
      "topic": "architecture"
    }
  ]
}
```

### CSV

Tabular format for spreadsheet analysis.

## Chunking Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `conversation` | Split by time gaps + size | General use (recommended) |
| `fixed` | Fixed token count | Simple cases |
| `topic` | One chunk per topic | Forum groups |
| `daily` | One chunk per day | Long time periods |

## Configuration

Create `~/.config/tg-parser/config.toml`:

```toml
[default]
output_format = "markdown"
output_dir = "~/Documents/tg-exports"

[filtering]
exclude_service = true
min_message_length = 0

[chunking]
strategy = "conversation"
max_tokens = 3000
time_gap_minutes = 30

[token_counter]
backend = "tiktoken"  # or "simple" for no deps
```

## Development

```bash
# Clone and setup
git clone https://github.com/example/tg-parser
cd tg-parser
uv sync --all-extras

# Run tests
uv run pytest

# Type check
uv run pyright

# Lint and format
uv run ruff check --fix
uv run ruff format

# Run CLI in dev mode
uv run tg-parser parse ./test.json
```

## Architecture

Clean Architecture with clear separation:

```
presentation/  →  application/  →  domain/  ←  infrastructure/
   (CLI, MCP)     (use cases)    (entities)    (adapters)
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** — AI assistant system prompt and development methodology
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Clean Architecture layers, domain model, design decisions
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** — Development guide, common tasks, testing guidelines
- **[docs/TELEGRAM_FORMAT.md](docs/TELEGRAM_FORMAT.md)** — Telegram JSON export format specification
- **[PRD.md](PRD.md)** — Product requirements, roadmap, implementation status
- **[CHANGELOG.md](CHANGELOG.md)** — Version history and release notes

## Development Status

**Current Version:** 1.0.0 (Stable)

| Component | Status | Details |
|-----------|--------|---------|
| Core parsing | ✅ Complete | All chat types, topics, reactions |
| Filtering | ✅ Complete | 9 filter types |
| Chunking | ✅ Complete | 3 strategies (fixed, topic, hybrid) |
| Streaming | ✅ Complete | ijson reader, auto-detection >50MB |
| CLI | ✅ Complete | 4 commands: `parse`, `stats`, `chunk`, `mentions` |
| MCP Server | ✅ Complete | 6 tools for Claude integration |
| Writers | ✅ Complete | Markdown, JSON, KB-template |
| Tests | ✅ Complete | 261 tests, pyright strict |
| PyPI | ✅ Published | v1.0.0 available |
| CI/CD | ✅ Automated | GitHub Actions for testing & releases |

### Roadmap

- **v1.0.0**: ✅ **RELEASED** - Production stable, PyPI published, CI/CD automated
- **v1.1.0**: CSV output, split-topics command, tiktoken integration

See [PRD.md](PRD.md) for detailed roadmap.

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Make changes with tests
4. Ensure `uv run pytest` and `uv run pyright` pass
5. Submit PR

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Telegram Desktop](https://desktop.telegram.org/) for export functionality
- [Typer](https://typer.tiangolo.com/) for CLI framework
- [MCP](https://modelcontextprotocol.io/) for Claude integration