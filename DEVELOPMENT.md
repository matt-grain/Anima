# Developing Anima

This guide is for working on **Anima itself**. If you just want to *use* Anima,
see the [README](README.md).

## Prerequisites

- [uv](https://github.com/astral-sh/uv) (package manager — never use pip/poetry directly)
- Python 3.13

```bash
git clone https://github.com/matt-grain/Anima.git
cd Anima
uv sync
```

## Local Development Setup

Point the global Claude Code configuration at your local checkout instead of an
installed release:

```bash
uv run anima setup --local --mode mcp
```

This makes the global MCP server and hooks run from this repo, so your code
changes take effect on the next session (or server restart).

## Running the Dev Server

A single server hosts both the MCP tools (`/mcp`) and the lifecycle hooks
(`/hooks/*`):

```bash
uv run anima serve --debug --reload   # verbose logs + auto-reload on file changes
```

- **`--reload`** watches `anima/` and restarts on changes.
- **`--debug`** raises log level to DEBUG.

### MCP transport

The MCP server defaults to **streamable-HTTP** (stdio hangs on Windows — the
response never reaches the client even though the memory is written). Claude
Code connects by URL:

```jsonc
// ~/.claude.json
"anima": { "type": "http", "url": "http://127.0.0.1:3741/mcp" }
```

The legacy stdio transport is still available for non-Windows use:

```bash
uv run anima --server --stdio
```

## Quality Gate

Run all of these before committing:

```bash
uv run pytest                 # tests
uv run pyright                # type checking (strict)
uv run ruff check . --fix     # lint + autofix
uv run ruff format .          # formatting
```

## Project Layout

| Path                          | Responsibility                                      |
|-------------------------------|-----------------------------------------------------|
| `anima/server.py`             | MCP server (FastMCP tools: memory, curiosity, …)    |
| `anima/http_server.py`        | HTTP server — hooks (`/hooks/*`) + MCP (`/mcp`)      |
| `anima/cli.py`                | CLI entry point (`anima <command>`)                 |
| `anima/hooks/`                | Session lifecycle hooks (start, end, subagent, …)   |
| `anima/storage/`              | SQLite persistence, migrations, subconscious index  |
| `anima/lifecycle/injection.py`| Memory injection + priority sorting                 |
| `anima/embeddings/`           | FastEmbed/ONNX semantic embeddings                  |
| `anima/commands/`             | CLI subcommands (recall, forget, dream, …)          |
| `anima/tools/`                | Setup, keygen, version/update, seed import          |
| `seeds/`                      | Starter memories planted on first install           |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the DSL, database schema, and token
budgeting system, and [CLAUDE.md](CLAUDE.md) for agent-facing conventions.

## Conventions

- Files stay under ~200 lines; functions under ~30.
- Full type annotations on public functions; no unjustified `Any`.
- Every feature ships with at least one happy-path and one error-path test.
- On Windows, the CLI forces UTF-8 I/O — keep new file reads/writes explicit
  (`encoding="utf-8"`) to avoid cp1252 crashes.
