# semtree

[![PyPI version](https://img.shields.io/pypi/v/semtree.svg)](https://pypi.org/project/semtree/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![CI](https://github.com/nikolasdehor/semtree/actions/workflows/ci.yml/badge.svg)](https://github.com/nikolasdehor/semtree/actions/workflows/ci.yml)

**Semantic code trees for AI assistants**

semtree indexes your codebase with tree-sitter, extracts symbols and docstrings across Python, JavaScript/TypeScript, Go, Rust, Java, C/C++, and more, and delivers token-optimized context to AI coding assistants. It exposes three MCP tools (`index_project`, `get_context`, `search_symbols`) that Claude Code, Cursor, Copilot, and Codex can call directly, and an intent classifier that selects the right retrieval strategy based on what you are trying to do.

---

## Quick Start

```bash
pip install "semtree[all]"
semtree index
semtree setup --target all
```

The `setup` command writes config files for every assistant automatically (see [MCP Integration](#mcp-integration)).

---

## Token savings

Feeding raw source files to an AI assistant wastes context. semtree extracts only the symbols relevant to your task.

```
Before  45,000 tokens  (entire src/ directory pasted into context)
After    6,000 tokens  (semtree context "add rate limiting to the API")

Savings: ~87%
```

The context budget is configurable (default: 8,000 tokens). Pass `--budget` on the CLI or set `default_token_budget` in `.ctx/semtree.json`.

---

## Why semtree vs context-lens

| Feature | semtree | context-lens |
|---|---|---|
| Multi-language docstrings (Python, JS/TS, Go, Rust) | Yes | Python only |
| MCP auto-config (.claude/mcp.json) | Yes | Manual |
| Hook debounce (2s cooldown) | Yes | No (fires every write) |
| Git temporal context (author, date) | Yes | No |
| Intent detection confidence | Weighted scoring | Regex 30% |
| Typed store returns | Dataclasses | Raw sqlite3.Row |
| Modular CLI | Click groups | 1000-line monolith |
| Concurrent-safe indexing | Lock file | No protection |

---

## Architecture

```
CLI (semtree)
     |
     v
Indexer (coordinator.py)
  walk -> SHA-1 hash -> tree-sitter parse -> extract symbols -> git blame
     |
     v
SQLite (.ctx/index.db)
  files | symbols (FTS5) | memory
     |
     v
Retrieval (retrieval/)
  intent classifier -> search.py -> policy.py
     |
     v
Context Builder (context/builder.py)
  budget.py + levels.py -> Markdown output
     |
     v
MCP Server (mcp.py)
  index_project | get_context | search_symbols
     |
     v
AI Assistant (Claude Code / Cursor / Copilot / Codex)
```

---

## CLI commands

```
semtree index                    Index the project (incremental by default)
semtree index --force            Re-index all files, ignoring cache
semtree context "QUERY"          Build context for a task, print to stdout
semtree context "QUERY" -b 4000  Limit context to 4,000 tokens
semtree context "QUERY" -l 0     Override detail level (0=minimal, 3=full)
semtree context "QUERY" -f FILE  Restrict context to a single file
semtree context "QUERY" -o FILE  Write context to a file instead of stdout
semtree search "QUERY"           Search symbols by name or keyword
semtree search "QUERY" -k class  Filter by kind (function|class|method|const|type|var)
semtree search "QUERY" --json    Output results as JSON
semtree status                   Show index stats (files, symbols, last updated)
semtree memory add rule KEY VAL  Store a project rule in the index
semtree memory add ref  KEY VAL  Store a file or URL reference
semtree memory add note KEY VAL  Store a freeform note
semtree memory list              List all memory entries
semtree memory list -k rule      List only rules
semtree memory remove rule KEY   Remove a memory entry
semtree setup --target all       Configure all AI assistants (writes config files)
semtree setup --target claude    Configure Claude Code only
semtree setup --dry-run          Preview setup changes without writing
semtree config                   Print current config as JSON
semtree config --init            Write default config to .ctx/semtree.json
```

---

## MCP Integration

### Automatic (recommended)

```bash
semtree setup --target claude
```

This creates or updates `.claude/mcp.json` in your project root with the `semtree-mcp` server entry. Restart Claude Code and the three MCP tools appear automatically.

### Manual

Add to `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "semtree": {
      "command": "semtree-mcp",
      "args": [],
      "env": {
        "SEMTREE_ROOT": "/path/to/your/project"
      }
    }
  }
}
```

### Available MCP tools

| Tool | Description |
|---|---|
| `index_project` | Index (or re-index) the project. Returns file and symbol counts. |
| `get_context` | Build a context string for a task query within a token budget. |
| `search_symbols` | Search symbols by name or keyword with optional kind filter. |

### Other assistants

`semtree setup --target cursor` writes `.cursor/mcp.json`.

`semtree setup --target copilot` adds a context instruction to `.vscode/settings.json`.

`semtree setup --target codex` appends a context block to `AGENTS.md` (or `CODEX.md`).

---

## Configuration

semtree reads `.ctx/semtree.json` in the project root. Run `semtree config --init` to write a config file with all defaults.

```json
{
  "include_extensions": [".py", ".js", ".ts", ".tsx", ".jsx",
                         ".go", ".rs", ".java", ".c", ".cpp",
                         ".h", ".hpp", ".rb", ".php", ".swift",
                         ".kt", ".cs", ".md", ".yaml", ".toml", ".json"],
  "exclude_dirs": [".git", "node_modules", "__pycache__", ".venv",
                   "dist", "build", "target", ".ctx"],
  "max_file_size_kb": 512,
  "use_gitignore": true,
  "default_token_budget": 8000,
  "git_context": true,
  "mcp_host": "127.0.0.1",
  "mcp_port": 5137
}
```

| Key | Default | Description |
|---|---|---|
| `include_extensions` | (list above) | File extensions to index |
| `exclude_dirs` | (list above) | Directories to skip |
| `max_file_size_kb` | `512` | Skip files larger than this |
| `use_gitignore` | `true` | Respect `.gitignore` patterns |
| `default_token_budget` | `8000` | Default token limit for context output |
| `git_context` | `true` | Annotate symbols with git author and date |
| `mcp_host` | `127.0.0.1` | MCP server bind host |
| `mcp_port` | `5137` | MCP server port |

---

## Installation

Install with all optional dependencies (recommended):

```bash
pip install "semtree[all]"
```

Install only what you need:

```bash
pip install semtree            # CLI only (no parsing, no tokens, no MCP)
pip install "semtree[parse]"   # + tree-sitter parsers (required for indexing)
pip install "semtree[tokens]"  # + tiktoken (accurate token counting)
pip install "semtree[mcp]"     # + MCP server support
```

Requirements: Python 3.11+, SQLite 3.35+ (bundled with Python).

---

## Project layout

After the first `semtree index`, a `.ctx/` directory is created in your project root:

```
.ctx/
  index.db       SQLite database (files, symbols with FTS5, memory)
  semtree.json   Config (created by semtree config --init)
  indexing.lock  Lock file preventing concurrent writes
```

Add `.ctx/index.db` to `.gitignore` if you do not want to commit the index.

---

## License

MIT. See [LICENSE](LICENSE).
