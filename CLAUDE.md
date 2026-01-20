# CLAUDE.md — AI Assistant System Prompt

> **Purpose:** Compact system instructions for AI assistants working on tg-parser project.

## Project Overview

**tg-parser** is a production-ready Python CLI/MCP tool for parsing Telegram Desktop JSON exports and preparing them for LLM processing.

**Primary use case:** Parse corporate Telegram chats → clean & chunk data → summarize with Claude.

**Current version:** v1.2.0

**Architecture:** Clean Architecture (domain/application/infrastructure/presentation)

## Quick Status

### What Works ✅

- **CLI:** 7 commands (`parse`, `stats`, `chunk`, `mentions`, `split-topics`, `mcp-config`, `config`)
- **MCP:** 6 tools for Claude Desktop/Code integration
- **Parsing:** All chat types (personal, group, supergroup, forum, channel)
- **Filtering:** 9 filter types (date, sender, topic, content, etc.)
- **Chunking:** 3 strategies (fixed, topic, hybrid)
- **Streaming:** ijson-based for files >50MB (auto-detection)
- **Output:** Markdown, JSON, KB-template, CSV formats
- **Token counting:** tiktoken integration (with SimpleTokenCounter fallback)
- **Config:** TOML config file support with discovery (`config show/init/path`)
- **Quality:** 413 tests, pyright strict mode
- **GitHub:** https://github.com/mdemyanov/tg-parser
- **PyPI:** Published v1.2.0 - `pip install tg-parser`
- **CI/CD:** 4 automated workflows (tests, typecheck, lint, publish)

### What's Missing ❌

- (All planned features for v1.2.0 implemented)

## Core Principles

1. **Immutable entities** — `@dataclass(frozen=True, slots=True)`
2. **Protocol-based DI** — Define in `domain/protocols/`, implement in `infrastructure/`
3. **Type safety** — pyright strict, no `Any`, use `| None` not `Optional`
4. **Explicit over implicit** — Clear data flow, no magic
5. **Fail fast** — Raise domain exceptions with actionable messages

## Tech Stack

- **Python:** 3.11+ (use modern syntax: `match`, `|`, `Self`)
- **Package manager:** uv (NOT pip/poetry)
- **Formatter/Linter:** ruff
- **Type checker:** pyright (strict mode)
- **Test framework:** pytest

## File Locations Reference

| Component | Path |
|-----------|------|
| Domain entities | `src/tg_parser/domain/entities/` |
| Value objects | `src/tg_parser/domain/value_objects/` |
| Protocols | `src/tg_parser/domain/protocols/` |
| Use cases | `src/tg_parser/application/use_cases/` |
| Readers | `src/tg_parser/infrastructure/readers/` |
| Writers | `src/tg_parser/infrastructure/writers/` |
| Filters | `src/tg_parser/infrastructure/filters/` |
| Chunkers | `src/tg_parser/infrastructure/chunkers/` |
| CLI commands | `src/tg_parser/presentation/cli/commands/` |
| MCP server | `src/tg_parser/presentation/mcp/server.py` |
| Tests | `tests/` (261 tests) |

## Development Commands

```bash
# Setup
uv sync --all-extras

# Run CLI/MCP
uv run tg-parser parse ./export.json
uv run tg-parser mcp

# Quality checks
uv run pytest          # Run tests
uv run pyright         # Type check
uv run ruff check --fix && uv run ruff format  # Lint & format
```

## Phase-Based Development Methodology

### Overview

Complex features are implemented in phases with clear deliverables and documentation updates at each stage.

### Phase Template

Each phase MUST follow this structure:

#### 1. Phase Prompt

Create a detailed prompt describing:
- **Goal:** What this phase achieves
- **Scope:** What is included/excluded
- **Acceptance criteria:** How to verify success
- **Implementation checklist:** Step-by-step tasks

**Example:**
```markdown
## Phase 2: CSV Output Writer

**Goal:** Implement CSV export format for tabular data analysis.

**Scope:**
- ✅ CSVWriter in infrastructure/writers/
- ✅ CLI flag `--format csv` in parse command
- ✅ Unit tests for CSVWriter
- ❌ MCP tool support (deferred to Phase 3)

**Acceptance Criteria:**
- [ ] `tg-parser parse ./export.json -f csv` produces valid CSV
- [ ] Headers: timestamp, author, text, topic, reactions
- [ ] Special characters properly escaped
- [ ] 10+ unit tests for edge cases

**Implementation:**
1. Create CSVWriter class implementing WriterProtocol
2. Register in writer factory
3. Add CLI option in parse.py
4. Write tests
5. Update documentation
```

#### 2. Documentation Update Requirements

**CRITICAL:** After completing each phase, you MUST update:

1. **[PRD.md](PRD.md):**
   - Move completed items from "Не реализовано ❌" to appropriate phase
   - Update implementation status table
   - Update test count if new tests added

2. **[README.md](README.md):**
   - If user-facing feature: move from "Coming Soon 🚧" to "Implemented ✅"
   - Update CLI reference if new commands/flags added
   - Update examples if relevant

3. **[CHANGELOG.md](CHANGELOG.md)** (if exists, else create):
   - Add entry under appropriate version section
   - Format: `- [Feature] Description of what was added`

4. **Architecture docs** (if structure changed):
   - [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): Update if new layers/patterns
   - [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md): Add guides for new patterns

#### 3. Next Phase Prompt Generation

After completing and documenting a phase:

1. **Review roadmap** in [PRD.md](PRD.md) to identify next priority
2. **Check dependencies** — ensure prerequisites are met
3. **Generate next phase prompt** using this template:

```markdown
## Phase N: [Feature Name]

**Previous phase completed:** Phase N-1 ([Brief description])

**Goal:** [What this phase achieves]

**Why now:** [Why this is the next priority based on roadmap/dependencies]

**Scope:**
- ✅ [What's included - bulleted list]
- ❌ [What's explicitly excluded - deferred items]

**Prerequisites:**
- [x] [Completed dependency 1]
- [x] [Completed dependency 2]

**Acceptance Criteria:**
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]
- [ ] [Documentation updated]
- [ ] [Tests passing]

**Implementation Checklist:**
1. [Step 1 with file paths]
2. [Step 2 with file paths]
...

**Estimated Complexity:** [Low/Medium/High]
**Priority:** [P0/P1/P2/P3 from PRD]
```

#### 4. All Phases Complete — Final Verification

When ALL phases in the roadmap are completed:

1. **Run comprehensive verification:**
   ```bash
   # Type check
   uv run pyright

   # All tests
   uv run pytest -v

   # Lint
   uv run ruff check

   # CLI smoke tests
   uv run tg-parser parse tests/fixtures/personal_chat.json
   uv run tg-parser stats tests/fixtures/supergroup_forum.json
   uv run tg-parser chunk tests/fixtures/personal_chat.json
   ```

2. **Update ALL documentation for consistency:**
   - [PRD.md](PRD.md): Mark all phases complete, update version to next major
   - [README.md](README.md): Ensure "Coming Soon" is empty, all features listed
   - [CLAUDE.md](CLAUDE.md): Update "What Works ✅" section, remove from "What's Missing ❌"
   - [CHANGELOG.md](CHANGELOG.md): Finalize version section
   - Version files: Update `__version__` in code, pyproject.toml

3. **Verify cross-document consistency:**
   ```bash
   # Check version consistency
   grep -n "v0\." *.md docs/*.md pyproject.toml src/tg_parser/__init__.py

   # Check test count consistency
   grep -n "test" *.md | grep -E "[0-9]+ test"

   # Check feature lists alignment
   grep -n "CLI:" *.md
   grep -n "MCP" *.md
   ```

4. **Create final verification checklist:**
   - [ ] All roadmap phases marked complete in PRD.md
   - [ ] README.md reflects all features
   - [ ] CLAUDE.md "What's Missing" only has truly missing items
   - [ ] Version numbers consistent across all files
   - [ ] Test counts consistent
   - [ ] CLI commands count consistent
   - [ ] MCP tools count consistent
   - [ ] CHANGELOG.md complete for version
   - [ ] All tests passing (261+)
   - [ ] No pyright errors
   - [ ] No ruff warnings

5. **Prepare release:**
   - Tag version in git: `git tag v1.0.0`
   - Update GitHub release notes from CHANGELOG
   - Publish to PyPI (see CI/CD section in PRD.md)

## Detailed Documentation

For in-depth information, refer to:

- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Clean Architecture layers, domain model, design decisions
- **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)** — Common tasks, testing guidelines, CLI/MCP development
- **[docs/TELEGRAM_FORMAT.md](docs/TELEGRAM_FORMAT.md)** — Telegram JSON structure, field mappings, normalization
- **[PRD.md](PRD.md)** — Product requirements, roadmap, implementation status

## Critical Rules

1. **NEVER edit files without reading them first** — Use Read tool before Edit/Write
2. **ALWAYS run tests after changes** — `uv run pytest`
3. **ALWAYS type-check** — `uv run pyright`
4. **Update docs when adding features** — See Phase-Based Methodology above
5. **Follow naming conventions:**
   - Modules: `snake_case.py`
   - Classes: `PascalCase`
   - Functions: `snake_case()`
   - Constants: `SCREAMING_SNAKE_CASE`
6. **Use absolute imports** — `from tg_parser.domain.entities import Message`
7. **No backwards-compat hacks** — If unused, delete completely

## Quick Examples

### Adding a Filter

```python
# 1. Create filter
# infrastructure/filters/reaction_filter.py
class ReactionFilter(FilterProtocol):
    def matches(self, message: Message) -> bool:
        return sum(message.reactions.values()) >= self._min_reactions

# 2. Register in composite filter
# 3. Add CLI option
# 4. Write tests (see docs/DEVELOPMENT.md for details)
```

### Adding an MCP Tool

```python
# 1. Define in presentation/mcp/tools.py
TG_SEARCH_TOOL = Tool(name="tg_search", description="...", inputSchema={...})

# 2. Implement handler in presentation/mcp/server.py
# 3. Write integration tests (see docs/DEVELOPMENT.md)
```

---

**For AI Assistants:** This is your primary reference. When working on tg-parser:
1. Start here for context and rules
2. Consult detailed docs in `docs/` for specific patterns
3. Follow Phase-Based Methodology for new features
4. Keep documentation synchronized with code changes
