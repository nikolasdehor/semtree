"""semtree CLI - modular Click-based command interface.

Commands:
  semtree index    - index the current project
  semtree context  - print context for a task/query
  semtree search   - search for symbols
  semtree status   - show index stats
  semtree memory   - manage project memory (add/list/remove)
  semtree setup    - set up AI assistant integrations
  semtree config   - show or edit project config
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__, log
from .config import SemtreeConfig, db_path, find_project_root
from .db.schema import init_db

# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, "-V", "--version")
@click.option("--root", type=click.Path(), default=None, help="Project root (default: auto-detect)")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
@click.pass_context
def main(ctx: click.Context, root: str | None, verbose: bool) -> None:
    """semtree - Semantic code trees for AI assistants.

    Index your codebase once. Feed smart, token-efficient context to
    Claude, Cursor, Copilot, and Codex.
    """
    ctx.ensure_object(dict)
    resolved_root = Path(root).resolve() if root else find_project_root()
    ctx.obj["root"] = resolved_root
    log.configure(verbose=verbose)


# ---------------------------------------------------------------------------
# index
# ---------------------------------------------------------------------------

@main.command()
@click.option("--force", "-f", is_flag=True, default=False, help="Re-index all files (ignore cache)")
@click.option("--quiet", "-q", is_flag=True, default=False, help="Suppress progress output")
@click.pass_context
def index(ctx: click.Context, force: bool, quiet: bool) -> None:
    """Index the project. Re-runs incrementally by default."""
    from .indexer.coordinator import run_index

    root: Path = ctx.obj["root"]
    config = SemtreeConfig.load(root)

    click.echo(f"Indexing {root} ...")

    def progress(path: str, current: int, total: int) -> None:
        if not quiet:
            click.echo(f"\r  [{current}/{total}] {path[:60]:<60}", nl=False)

    stats = run_index(root, config=config, force=force, progress=progress if not quiet else None)

    if not quiet:
        click.echo()  # newline after progress

    click.echo(
        f"Done. {stats.new_files} new, {stats.updated_files} updated, "
        f"{stats.skipped_files} skipped, {stats.total_symbols} symbols "
        f"({stats.elapsed_seconds:.1f}s)"
    )
    if stats.errors:
        click.echo(f"Errors ({len(stats.errors)}):", err=True)
        for e in stats.errors[:5]:
            click.echo(f"  {e}", err=True)


# ---------------------------------------------------------------------------
# context
# ---------------------------------------------------------------------------

@main.command()
@click.argument("query")
@click.option("--budget", "-b", default=8000, show_default=True, help="Token budget")
@click.option("--level", "-l", type=click.IntRange(0, 3), default=None, help="Detail level 0-3")
@click.option("--file", "-f", "file_filter", default=None, help="Restrict to file path")
@click.option("--output", "-o", type=click.Path(), default=None, help="Write to file instead of stdout")
@click.pass_context
def context(
    ctx: click.Context,
    query: str,
    budget: int,
    level: int | None,
    file_filter: str | None,
    output: str | None,
) -> None:
    """Build context for a task and print it.

    QUERY is a natural language description of your task.
    """
    from .context.builder import build_context, build_context_for_file

    root: Path = ctx.obj["root"]
    conn = init_db(db_path(root))

    if file_filter:
        result = build_context_for_file(conn, file_filter, budget, level or 2)
    else:
        result = build_context(conn, query, budget, root, force_level=level)

    if output:
        Path(output).write_text(result)
        click.echo(f"Context written to {output}")
    else:
        click.echo(result)


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@main.command()
@click.argument("query")
@click.option("--kind", "-k", default=None, help="Filter by kind: function|class|method|const|type|var")
@click.option("--limit", "-n", default=20, show_default=True, help="Max results")
@click.option("--json", "as_json", is_flag=True, default=False, help="Output as JSON")
@click.pass_context
def search(ctx: click.Context, query: str, kind: str | None, limit: int, as_json: bool) -> None:
    """Search for symbols by name or keyword."""
    import json as _json

    from .retrieval.search import search as do_search

    root: Path = ctx.obj["root"]
    conn = init_db(db_path(root))
    results = do_search(conn, query, limit=limit)

    if kind:
        results = [r for r in results if r.symbol.kind == kind]

    if as_json:
        data = [
            {
                "name": r.symbol.name,
                "kind": r.symbol.kind,
                "file": r.symbol.file_path,
                "line": r.symbol.line_start,
                "signature": r.symbol.signature,
                "docstring": r.symbol.docstring[:100],
                "score": r.score,
            }
            for r in results
        ]
        click.echo(_json.dumps(data, indent=2))
    else:
        if not results:
            click.echo(f"No symbols found for '{query}'")
            return
        for r in results:
            sym = r.symbol
            doc_preview = sym.docstring.split("\n")[0][:60] if sym.docstring else ""
            click.echo(
                f"{sym.kind:10} {sym.name:40} {sym.file_path}:{sym.line_start}"
                + (f"\n           {doc_preview}" if doc_preview else "")
            )


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@main.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show index stats and configuration."""
    from .db import store as db_store

    root: Path = ctx.obj["root"]
    db = db_path(root)

    if not db.exists():
        click.echo("No index found. Run: semtree index")
        return

    conn = init_db(db)
    n_files = db_store.count_files(conn)
    n_symbols = db_store.count_symbols(conn)
    files = db_store.list_files(conn)
    latest = max((f.indexed_at for f in files), default=0.0) if files else 0.0

    import time
    age = int(time.time() - latest) if latest else 0
    age_str = f"{age}s ago" if age < 60 else f"{age // 60}m ago"

    config = SemtreeConfig.load(root)

    click.echo(f"Root:    {root}")
    click.echo(f"Index:   {db}")
    click.echo(f"Files:   {n_files}")
    click.echo(f"Symbols: {n_symbols}")
    click.echo(f"Updated: {age_str}")
    click.echo(f"Budget:  {config.default_token_budget} tokens")
    click.echo(f"Git ctx: {'yes' if config.git_context else 'no'}")


# ---------------------------------------------------------------------------
# memory
# ---------------------------------------------------------------------------

@main.group()
@click.pass_context
def memory(ctx: click.Context) -> None:
    """Manage project memory (rules, references, notes)."""
    pass


@memory.command("add")
@click.argument("kind", type=click.Choice(["rule", "ref", "note"]))
@click.argument("key")
@click.argument("value")
@click.pass_context
def memory_add(ctx: click.Context, kind: str, key: str, value: str) -> None:
    """Add or update a memory entry.

    KIND: rule | ref | note
    KEY:  short identifier
    VALUE: the content
    """
    from .memory.lite import ProjectMemory

    root: Path = ctx.obj["root"]
    conn = init_db(db_path(root))
    mem = ProjectMemory(conn)
    mem.add(kind, key, value)
    click.echo(f"Stored [{kind}] {key}")


@memory.command("list")
@click.option("--kind", "-k", default=None, type=click.Choice(["rule", "ref", "note"]))
@click.pass_context
def memory_list(ctx: click.Context, kind: str | None) -> None:
    """List all memory entries."""
    from .memory.lite import ProjectMemory

    root: Path = ctx.obj["root"]
    conn = init_db(db_path(root))
    mem = ProjectMemory(conn)
    records = mem.list_all(kind)
    if not records:
        click.echo("No memory entries found.")
        return
    for rec in records:
        click.echo(f"[{rec.kind}] {rec.key}: {rec.value}")


@memory.command("remove")
@click.argument("kind", type=click.Choice(["rule", "ref", "note"]))
@click.argument("key")
@click.pass_context
def memory_remove(ctx: click.Context, kind: str, key: str) -> None:
    """Remove a memory entry."""
    from .memory.lite import ProjectMemory

    root: Path = ctx.obj["root"]
    conn = init_db(db_path(root))
    mem = ProjectMemory(conn)
    removed = mem.remove(kind, key)
    if removed:
        click.echo(f"Removed [{kind}] {key}")
    else:
        click.echo(f"Entry not found: [{kind}] {key}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

@main.command()
@click.option(
    "--target",
    "-t",
    default="all",
    type=click.Choice(["claude", "cursor", "copilot", "codex", "all"]),
    show_default=True,
    help="Which AI assistant to configure",
)
@click.option("--dry-run", is_flag=True, default=False, help="Preview changes without writing")
@click.option("--host", default="127.0.0.1", show_default=True, help="MCP server host")
@click.option("--port", default=5137, show_default=True, help="MCP server port")
@click.pass_context
def setup(
    ctx: click.Context,
    target: str,
    dry_run: bool,
    host: str,
    port: int,
) -> None:
    """Set up AI assistant integrations.

    Creates config files for Claude Code (.claude/mcp.json),
    Cursor (.cursor/mcp.json), Copilot (.vscode/settings.json),
    and Codex (AGENTS.md).
    """
    from .scripts.setup import setup_integration

    root: Path = ctx.obj["root"]
    if dry_run:
        click.echo("[dry-run] No files will be written.\n")

    results = setup_integration(root, target=target, dry_run=dry_run, host=host, port=port)

    for path, action in results.items():
        icon = "+" if "created" in action else ("~" if "updated" in action else "-")
        click.echo(f"  {icon} {path}: {action}")

    if not dry_run:
        click.echo("\nSetup complete. Run 'semtree index' to build the index.")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

@main.command("config")
@click.option("--show", is_flag=True, default=False, help="Print current config as JSON")
@click.option("--init", is_flag=True, default=False, help="Write default config to .ctx/semtree.json")
@click.pass_context
def config_cmd(ctx: click.Context, show: bool, init: bool) -> None:
    """Show or initialize project configuration."""
    import json

    root: Path = ctx.obj["root"]
    cfg = SemtreeConfig.load(root)

    if init:
        cfg.save(root)
        click.echo(f"Config written to {root / '.ctx' / 'semtree.json'}")
        return

    if show or not init:
        data = {
            "root": str(root),
            "include_extensions": cfg.include_extensions,
            "exclude_dirs": cfg.exclude_dirs,
            "max_file_size_kb": cfg.max_file_size_kb,
            "use_gitignore": cfg.use_gitignore,
            "default_token_budget": cfg.default_token_budget,
            "git_context": cfg.git_context,
        }
        click.echo(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
