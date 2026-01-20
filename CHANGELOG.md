# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.2.0] - 2026-01-20

### Added
- **TOML configuration file support**: Set default CLI options via config files
  - Priority-based config discovery (CLI flag > env var > local > home > XDG)
  - `tg-parser config show` - display current effective configuration
  - `tg-parser config init` - create example configuration file
  - `tg-parser config path` - show config file search locations
  - Global `--config/-c` option for all commands
- **ConfigSettings value object**: Immutable configuration dataclass
- **ConfigLoader and FileConfigReader**: TOML parsing with Pydantic validation
- Config integration with all CLI commands (parse, chunk, stats, mentions, split-topics)
- 70 new tests for config infrastructure (total: 413 tests)

### Changed
- CLI commands now resolve defaults from config file when not specified via CLI
- All boolean flags (--no-frontmatter, --include-service, etc.) can be configured via TOML

### Documentation
- README.md: Added Configuration section with detailed usage examples
- CLAUDE.md: Updated Quick Status with config support
- PRD.md: Updated to v1.2.0 status

## [1.1.0] - 2026-01-20

### Added
- **CSV output format**: New `CSVWriter` for tabular data export (`-f csv`)
- **split-topics command**: Standalone CLI command for splitting chats by topic
- **tiktoken integration**: Accurate token counting with `TiktokenCounter`
  - Auto-detection: uses tiktoken if available, falls back to SimpleTokenCounter
  - Factory function `get_token_counter()` for backend selection
- **mcp-config command**: Auto-configure Claude Desktop/Code MCP integration
  - Automatic venv detection (uses venv Python or uvx)
  - Support for Claude Desktop and Claude Code targets
  - Dry-run mode and backup creation
  - Platform-aware config path detection (macOS, Windows, Linux)
- 82 new tests for split-topics, CSV writer, tiktoken, and mcp-config (total: 343 tests)

### Changed
- All writers and use-cases now use `get_token_counter()` factory
- Ruff configuration updated to ignore intentional patterns (PLC0415, TC001, TC003)
- Fixed 2 flaky tests in `TestExtractionGuideFlag` (Rich console truncation)

### Documentation
- Updated README.md with v1.1.0 features
- Updated CLAUDE.md Quick Status section
- Incremented version to 1.1.0 in all files

## [1.0.0] - 2026-01-19

### Added
- **GitHub repository** at https://github.com/mdemyanov/tg-parser
- **CI/CD pipeline** with 4 GitHub Actions workflows:
  - Tests workflow (pytest on Python 3.11 & 3.12 with coverage)
  - Type check workflow (pyright strict mode)
  - Lint workflow (ruff check and format)
  - Publish workflow (automated PyPI releases)
- **PyPI publication** - package available as `pip install tg-parser`
- GitHub repository metadata (topics, description, issues enabled)
- GitHub Secrets for automated PyPI publishing

### Changed
- **Version synchronization**: Updated from 0.1.0 to 1.0.0 across all files
- Development status: Alpha → Production/Stable
- Documentation updated to reflect published status

### Documentation
- README.md updated with PyPI installation instructions
- CHANGELOG.md version comparison URLs updated
- All placeholder "username" URLs replaced with "mdemyanov"
- Added project URLs: Issues, Changelog

## [0.3.0] - 2025-01-19

### Added
- **Streaming support** for large files (>50MB) using ijson
- TelegramStreamReader with automatic file size detection
- Progress bars in CLI using rich.progress
- `--streaming` / `--no-streaming` CLI flags for manual control
- Graceful fallback when ijson is not installed
- StreamingError exception for streaming-related errors
- 76 new tests for streaming functionality (total: 261 tests)

### Changed
- Reader factory now auto-detects streaming mode based on file size (>50MB threshold)
- All MCP tools now support streaming parameter
- Improved memory efficiency for large exports (O(n) → O(1) in streaming mode)

### Documentation
- Updated README.md to reflect v0.3.0 status
- Updated PRD.md with Phase 5 completion
- Updated CLAUDE.md with streaming information
- Restructured documentation into docs/ directory
- Created ARCHITECTURE.md, DEVELOPMENT.md, TELEGRAM_FORMAT.md

## [0.2.5] - 2025-01-10

### Added
- JSONWriter for structured JSON output
- KBTemplateWriter with YAML frontmatter
- Advanced filtering: topic, content regex, attachment, forward
- CompositeFilter with AND logic
- `list_mentioned_users` MCP tool
- CLI support for extended filters

### Changed
- Improved filter composability
- Enhanced mention extraction

## [0.2.0] - 2025-01-05

### Added
- **Chunking strategies**: FixedChunker, TopicChunker, HybridChunker, DailyChunker, ConversationChunker
- `chunk` CLI command with multiple strategies
- `chunk_telegram_export` MCP tool
- `--split-topics` flag in parse command
- Chunk and ChunkMetadata entities
- SimpleTokenCounter for token estimation

### Changed
- Improved topic-based message grouping
- Enhanced chunking for LLM context limits

### Documentation
- Added chunking strategies guide to README
- Updated PRD with Phase 2 completion

## [0.1.0] - 2024-12-20

### Added
- **Core parsing** for all Telegram chat types (personal, group, supergroup, forum, channel)
- **Domain model**: Message, Chat, Topic, Participant entities
- **Value objects**: FilterSpecification, DateRange, MessageId, UserId, TopicId
- **Filtering**: 9 filter types (date, sender, topic, content, attachment, reactions, forwards, service, composite)
- **CLI commands**: `parse`, `stats`, `mentions`
- **MCP server** with 6 tools:
  - `parse_telegram_export`
  - `get_chat_statistics`
  - `list_chat_participants`
  - `list_chat_topics`
  - `chunk_telegram_export`
  - `list_mentioned_users`
- **Output formats**: Markdown (LLM-optimized)
- **Clean Architecture** with strict layer separation
- **Type safety**: pyright strict mode compliance
- **Testing**: 185 unit and integration tests
- TelegramJSONReader for standard JSON parsing
- MarkdownWriter with LLM-optimized output

### Documentation
- Initial README.md with installation and usage
- PRD.md with product requirements and roadmap
- CLAUDE.md with AI assistant instructions

## [0.0.1] - 2024-12-01

### Added
- Initial project structure
- Basic domain entities (Message, Chat)
- Proof of concept parser for personal chats

---

## Version History Summary

- **v1.2.0** (2026-01-20): TOML config file support, `config` command group, 413 tests
- **v1.1.0** (2026-01-20): CSV export, split-topics, tiktoken, mcp-config, 343 tests
- **v1.0.0** (2026-01-19): GitHub publication, PyPI release, CI/CD
- **v0.3.0** (2025-01-19): Streaming support for large files, 261 tests
- **v0.2.5** (2025-01-10): Advanced filtering, JSON/KB-template writers
- **v0.2.0** (2025-01-05): Chunking strategies, split-topics support
- **v0.1.0** (2024-12-20): MVP with CLI, MCP server, core parsing
- **v0.0.1** (2024-12-01): Initial prototype

[Unreleased]: https://github.com/mdemyanov/tg-parser/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/mdemyanov/tg-parser/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/mdemyanov/tg-parser/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/mdemyanov/tg-parser/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/mdemyanov/tg-parser/compare/v0.2.5...v0.3.0
[0.2.5]: https://github.com/mdemyanov/tg-parser/compare/v0.2.0...v0.2.5
[0.2.0]: https://github.com/mdemyanov/tg-parser/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mdemyanov/tg-parser/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/mdemyanov/tg-parser/releases/tag/v0.0.1
