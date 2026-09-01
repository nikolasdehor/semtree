<p align="center">
  <img src="https://img.shields.io/badge/semtree-structural%20context-0d1117?style=for-the-badge&labelColor=0d1117&color=6e40c9" alt="semtree" height="48">
</p>

<p align="center">
  <strong>Semtree seleciona contexto estrutural para AI assistants</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/semtree/"><img src="https://img.shields.io/pypi/v/semtree?color=6e40c9&label=PyPI" alt="PyPI version"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11%2B-3776ab?logo=python&logoColor=white" alt="Python 3.11+"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22c55e" alt="License MIT"></a>
  <a href="https://github.com/DeHor-Labs/semtree/actions/workflows/ci.yml"><img src="https://github.com/DeHor-Labs/semtree/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/github/stars/DeHor-Labs/semtree?style=flat&color=6e40c9" alt="Stars">
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> ·
  <a href="#features">Features</a> ·
  <a href="#cli-commands">CLI</a> ·
  <a href="#mcp-integration">MCP</a> ·
  <a href="#scope-and-limits">Scope</a>
</p>

---

**Pare de colar arquivos inteiros no seu assistente de IA.** Com as gramáticas opcionais instaladas, o Semtree usa tree-sitter para extrair símbolos suportados, assinaturas e docstrings e montar contexto dentro de um orçamento configurável. Sem elas, há fallbacks limitados para parte das linguagens.

O Semtree inclui um [benchmark local](docs/benchmarks.md) que compara o volume bruto de um projeto sintético com o contexto recuperado para consultas definidas no próprio script. Ele mede o seu ambiente sem prometer uma redução fixa. O Semtree expõe ferramentas MCP (`index_project`, `get_context`, `search_symbols`) para indexar, buscar símbolos e montar contexto estrutural.

---

## Quick Start

```bash
pip install "semtree[all]"
semtree index
semtree setup --target all
```

The `setup` command writes MCP configuration to `.mcp.json` for Claude Code and `.cursor/mcp.json` for Cursor, and CLI context instructions for Copilot and Codex (see [MCP Integration](#mcp-integration)).

---

## Token Budgeting

Feeding raw source files to an AI assistant can consume more context than a task needs. Semtree selects symbols that match the query within a configurable budget.

The reduction depends on repository size, query, language support, index state, and the configured budget. The bundled benchmark measures a synthetic project and prints the result from the version running locally; it is not a fixed performance promise.

The context budget is configurable (default: 8,000 tokens). Pass `--budget` on the CLI or set `default_token_budget` in `.ctx/semtree.json`. See [Benchmark local](docs/benchmarks.md) to reproduce the current comparison.

---

## Features

**Multi-language symbol extraction**
With the `parse` extra installed, tree-sitter parses Python, JavaScript, TypeScript, Go, Rust, Java, C, and C++. Visitors específicos extraem as declarações implementadas para cada linguagem, com assinaturas, docstrings disponíveis e metadados de Git.

**Intent-aware retrieval**
The intent classifier scores explicit query patterns and selects a policy that controls preferred symbol kinds, detail level, limits, and optional file-tree output.

**Token-budgeted context builder**
Context output is shaped to a configurable token budget. The detail level (0 = symbol names and kinds, 3 = full docstrings + git context) is chosen automatically or overridden per call.

**Assistant setup**
`semtree setup` writes `.mcp.json` for Claude Code and `.cursor/mcp.json` for Cursor. For Copilot and Codex, it adds instructions that call the `semtree context` CLI; those targets do not receive the three MCP tools from this setup.

**Project memory**
Store, list, and remove local rules, references, and notes in the index database. The current context builder does not append those entries automatically.

**Git temporal context**
Every symbol is annotated with the git author and date from `git blame`. Assistants can see who last touched a function and when.

**Incremental indexing**
SHA-1 hashes skip unchanged files. A local marker reduces overlapping indexing attempts, while SQLite transactions protect each write operation.

---

## Scope and limits

- Retrieval uses exact name matching, SQLite FTS5, and a prefix fallback; it is not semantic or vector search.
- Without the optional tree-sitter parsers, Python, JavaScript, TypeScript, Go, Rust, and Java use limited regular-expression fallbacks; C and C++ require their grammars for symbol extraction.
- The index stores symbols and available documentation, not imports, dependencies, references, or call graphs.
- Context selection can omit relevant code and does not replace file inspection, tests, or review.
- Token reduction varies by query, repository, parser coverage, and budget; the bundled benchmark measures volume only.
- Claude Code and Cursor can use the MCP tools. The built-in Copilot and Codex setup writes CLI instructions instead.

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
MCP Client (Claude Code / Cursor)
```

---

## CLI Commands

```
semtree index                    Index the project (incremental by default)
semtree index --force            Re-index all files, ignoring cache

semtree context "QUERY"          Build context for a task, print to stdout
semtree context "QUERY" -b 4000  Limit context to 4,000 tokens
semtree context "QUERY" -l 0     Override detail level (0=names/kinds, 3=full)
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

This creates or updates `.mcp.json` in your project root with the `semtree-mcp` server entry. Existing valid servers are preserved; invalid JSON or an invalid `mcpServers` value is left unchanged and reported as an error. The executable must be available in the PATH used by Claude Code. At runtime, Semtree uses the `CLAUDE_PROJECT_DIR` supplied by Claude Code, so the shared config does not contain a machine-specific checkout path.

Restart Claude Code after setup. Claude Code asks you to approve project-scoped servers from `.mcp.json` before first use; the tools become available only after that approval.

### Manual

Add to `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "semtree": {
      "command": "semtree-mcp",
      "args": []
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|---|---|
| `index_project` | Index (or re-index) the project. Returns file and symbol counts. |
| `get_context` | Build a context string for a task query within a token budget. |
| `search_symbols` | Search symbols by name or keyword with optional kind filter. |

### Other Assistants

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
                         ".kt", ".cs", ".md", ".txt", ".yaml", ".yml",
                         ".toml", ".json"],
  "exclude_dirs": [".git", ".hg", ".svn", "node_modules", "__pycache__",
                   ".venv", "venv", "env", ".env", "dist", "build",
                   "target", ".ctx", ".idea", ".vscode", "*.egg-info",
                   "coverage", ".coverage", "htmlcov"],
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
| `include_extensions` | (list above) | File extensions to scan; structural extraction covers the eight parser languages listed above |
| `exclude_dirs` | (list above) | Directories to skip |
| `max_file_size_kb` | `512` | Skip files larger than this |
| `use_gitignore` | `true` | Respect `.gitignore` patterns |
| `default_token_budget` | `8000` | Default token limit for context output |
| `git_context` | `true` | Annotate symbols with git author and date |
| `mcp_host` | `127.0.0.1` | Reserved configuration value; the current MCP server uses stdio |
| `mcp_port` | `5137` | Reserved configuration value; the current MCP server does not bind a port |

---

## Installation

Install with all optional dependencies (recommended):

```bash
pip install "semtree[all]"
```

Install only what you need:

```bash
pip install semtree            # CLI + limited regex fallback + approximate token counting
pip install "semtree[parse]"   # + tree-sitter parsers for structural extraction
pip install "semtree[tokens]"  # + tiktoken-based token counting
pip install "semtree[mcp]"     # + MCP server support
```

Requirements: Python 3.11+, SQLite 3.35+ (bundled with Python).

---

## Project Layout

After the first `semtree index`, a `.ctx/` directory is created in your project root:

```
.ctx/
  index.db       SQLite database (files, symbols with FTS5, memory)
  semtree.json   Config (created by semtree config --init)
  indexing.lock  Short-lived marker that reduces overlapping indexing attempts
```

Add `.ctx/index.db` to `.gitignore` if you do not want to commit the index.

---

## License

MIT. See [LICENSE](LICENSE).

---

<p align="center">
  Built by <a href="https://github.com/nikolasdehor">Nikolas de Hor</a>
  <br>
  <sub>Select structural context before sending code to your AI assistant</sub>
</p>
