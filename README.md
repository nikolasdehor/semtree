# semtree

[![PyPI version](https://img.shields.io/pypi/v/semtree.svg)](https://pypi.org/project/semtree/)
[![Python versions](https://img.shields.io/pypi/pyversions/semtree.svg)](https://pypi.org/project/semtree/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![CI](https://github.com/nikolasdehor/semtree/actions/workflows/ci.yml/badge.svg)](https://github.com/nikolasdehor/semtree/actions/workflows/ci.yml)

**Semantic code trees for AI assistants.** Index once, feed smart context to Claude, Cursor, and Copilot.

semtree indexes your codebase into a local SQLite database with FTS5 full-text search, classifies your task intent, and returns a token-budgeted context block that AI assistants can actually use - not a 50k-token file dump.

## Quick Start

```bash
pip install semtree
semtree index
semtree context "implement user authentication"
```

That's it. The third command outputs a focused context block you can paste into Claude or any AI assistant, or let the MCP server deliver it automatically.

## Why semtree?

Most "context for AI" tools either dump entire files or require cloud embeddings. semtree takes a different approach:

- **Local-first**: SQLite index, no cloud calls required
- **Intent-aware**: classifies your task (implement/debug/refactor/test/explain/review/search) and adjusts what context to include
- **Token-budgeted**: respects your token budget, trims gracefully, never wastes tokens on irrelevant code
- **Multi-language docstrings**: extracts Python docstrings, JS/TS JSDoc, Go comments, and Rust `///` doc comments
- **Git context**: optionally includes last-modified author/date per symbol so AI knows what's recent
- **MCP native**: one command to configure Claude Code, Cursor, and Copilot

## Feature Comparison

| Feature | semtree | context-lens |
|---------|---------|--------------|
| Full-text search (FTS5) | Yes | Yes |
| Intent classification | Weighted scoring, no stopword confusion | Basic keyword matching |
| Multi-language docstrings | Python, JS/TS, Go, Rust | Python only |
| Git blame context | Per-symbol author + date | No |
| Token budget management | tiktoken (accurate) + char fallback | Basic |
| MCP auto-config | `semtree setup --auto` writes .claude/mcp.json | Manual |
| Debounced indexing | 2s debounce + lock file | No |
| Project memory | rules/refs/notes stored in DB | No |
| Context levels L0-L3 | Progressive detail | Single level |
| Retrieval policies | Per-intent policies | No |

## Installation

```bash
# Minimal (just indexing + CLI)
pip install semtree

# With tree-sitter for accurate parsing
pip install "semtree[parse]"

# With tiktoken for accurate token counting
pip install "semtree[tokens]"

# With MCP server support
pip install "semtree[mcp]"

# Everything
pip install "semtree[all]"
```

## Usage

### Index your project

```bash
cd /path/to/your/project
semtree index
```

Re-runs incrementally - only changed files are re-parsed.

```bash
semtree index --force    # Re-index everything
semtree status           # Show index stats
```

### Get context for a task

```bash
semtree context "add rate limiting to the API"
semtree context "fix the memory leak in the connection pool" --budget 6000
semtree context "explain the authentication flow" --level 3
semtree context "implement payment" --file src/billing.py
```

### Search for symbols

```bash
semtree search authenticate
semtree search "database connection" --kind function
semtree search UserManager --json
```

### Project memory

Store project-specific rules that get injected into context:

```bash
semtree memory add rule style "Always use async/await for I/O operations"
semtree memory add ref docs "API docs at https://internal.docs/api"
semtree memory add note todo "Refactor auth module after Q1"
semtree memory list
semtree memory remove rule style
```

### Set up AI assistant integration

```bash
# Auto-configure all supported assistants
semtree setup

# Just Claude Code
semtree setup --target claude

# Preview what would be written
semtree setup --dry-run
```

This writes `.claude/mcp.json`, `.cursor/mcp.json`, and updates `.vscode/settings.json` automatically.

### MCP server

The MCP server exposes three tools to Claude Code and Cursor:

- `index_project` - (re)index the project
- `get_context` - get semantic context for a task
- `search_symbols` - search for specific symbols

Start it manually (usually not needed after `semtree setup`):

```bash
semtree-mcp
```

## Architecture

```
semtree/
  cli.py              CLI entry point (modular Click groups)
  config.py           Project root detection + config management
  mcp.py              MCP server (3 tools)
  db/
    schema.py         SQLite DDL: files, symbols, FTS5, memory tables
    store.py          CRUD with typed returns
  indexer/
    coordinator.py    Orchestration: walk -> hash -> parse -> store
    walker.py         File walker with .gitignore support
    hasher.py         SHA-1 incremental change detection
    parser.py         Tree-sitter parser pool (cached, thread-safe)
    extractor.py      Symbol extraction (tree-sitter + regex fallback)
    docstrings.py     Multi-language docstring extraction
    gitblame.py       Per-symbol git author/date
  retrieval/
    intent.py         Weighted intent classifier (7 intents)
    search.py         FTS5 + exact + prefix search
    policy.py         Per-intent retrieval policies
  context/
    budget.py         Token budget (tiktoken or char estimate)
    levels.py         L0-L3 context formatters
    builder.py        Context assembly orchestrator
  memory/
    lite.py           Project memory (rules/refs/notes)
  scripts/
    setup.py          AI assistant integration setup
```

### Token savings example

A typical FastAPI project with 150 files and 800 symbols:

| Approach | Tokens sent to AI |
|----------|------------------|
| Dump all files | ~180,000 |
| Dump file list only | ~2,000 |
| **semtree context (L2)** | **~4,000** |
| semtree context (L1 search intent) | ~1,500 |

semtree selects only the symbols relevant to your specific task, formats them at the appropriate detail level, and stays within your budget.

## Configuration

semtree stores its index in `.ctx/` at your project root. Configuration is in `.ctx/semtree.json`:

```json
{
  "include_extensions": [".py", ".js", ".ts", ".go", ".rs"],
  "exclude_dirs": ["node_modules", "__pycache__", ".venv"],
  "max_file_size_kb": 512,
  "use_gitignore": true,
  "default_token_budget": 8000,
  "git_context": true
}
```

Initialize with defaults:

```bash
semtree config --init
semtree config --show
```

## Requirements

- Python 3.11+
- SQLite 3.35+ (bundled with Python)
- `click>=8.0`, `pathspec>=0.12` (installed automatically)
- Optional: `tree-sitter>=0.25` for accurate parsing
- Optional: `tiktoken>=0.6` for accurate token counting
- Optional: `mcp>=1.0` for MCP server

## License

MIT. See [LICENSE](LICENSE).
