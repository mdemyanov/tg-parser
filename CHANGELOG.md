# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned for v1.1.0
- CSV output format
- Separate `split-topics` command (currently works via `--split-topics` flag)
- tiktoken integration for accurate token counting
- TOML configuration file support

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

- **v0.3.0** (2025-01-19): Streaming support for large files, 261 tests
- **v0.2.5** (2025-01-10): Advanced filtering, JSON/KB-template writers
- **v0.2.0** (2025-01-05): Chunking strategies, split-topics support
- **v0.1.0** (2024-12-20): MVP with CLI, MCP server, core parsing
- **v0.0.1** (2024-12-01): Initial prototype

[Unreleased]: https://github.com/mdemyanov/tg-parser/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/mdemyanov/tg-parser/compare/v0.3.0...v1.0.0
[0.3.0]: https://github.com/mdemyanov/tg-parser/compare/v0.2.5...v0.3.0
[0.2.5]: https://github.com/mdemyanov/tg-parser/compare/v0.2.0...v0.2.5
[0.2.0]: https://github.com/mdemyanov/tg-parser/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/mdemyanov/tg-parser/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/mdemyanov/tg-parser/releases/tag/v0.0.1
