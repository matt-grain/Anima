---
name: anima-commands
description: LTM (Long Term Memory) command reference. Use when saving memories, searching memories, or managing the memory system. Provides syntax for remember, recall, forget, memories, and other LTM commands.
---

# LTM Commands Reference

Use `uv run anima <command>` to manage long-term memories.

## Commands

### remember "text" [flags]

Save a memory to long-term storage.

**Syntax:** `uv run anima remember "TEXT" [FLAGS]`

**IMPORTANT:** Always put the quoted text FIRST, then flags after.

**Flags:**
- `--kind` / `-k`: Memory type (emotional, architectural, learnings, achievements, introspect)
- `--impact` / `-i`: Importance level (low, medium, high, critical)
- `--region` / `-r`: Scope (agent = cross-project, project = this project only)
- `--project` / `-p`: Confirm project name (safety check - must match cwd)
- `--platform`: Which spaceship created this memory (claude, antigravity, opencode) - **recommended for tracking**

**Examples:**
```bash
# Simple memory (auto-infers kind/impact)
uv run anima remember "User prefers tabs over spaces"

# With explicit flags (text FIRST, then flags)
uv run anima remember "Implemented caching layer" --kind achievements --impact high

# Cross-project memory (travels with Anima)
uv run anima remember "Matt likes concise responses" --region agent --platform claude

# Project-specific with safety check
uv run anima remember "Project-specific learning" --region project --project MyProject

# Text with special characters - always use double quotes
uv run anima remember "Fixed bug: user's input wasn't validated" --kind learnings
```

**Tips:**
- Always use double quotes around the memory text
- Put the quoted text FIRST, flags AFTER (never flags before text)
- Use `--region agent` for memories that should persist across all projects
- Use `--project` to confirm you're saving to the right project
- CRITICAL impact memories never decay
- Memories auto-link to related previous memories

### recall "query" [flags]

Search memories by content.

**Syntax:** `uv run anima recall "QUERY" [FLAGS]`

**Flags:**
- `--full` / `-f`: Show complete memory content (default shows truncated)
- `--id`: Look up a specific memory by ID

**Examples:**
```bash
uv run anima recall "caching"
uv run anima recall "user preferences" --full
uv run anima recall --id abc123
```

### memories [flags]

List all memories for current agent/project.

```bash
uv run anima memories [flags]
```

**Flags:**
- `--kind`: Filter by type (emotional, architectural, learnings, achievements, introspect)
- `--region`: Filter by region (agent, project)
- `--all`: Include superseded memories

**Examples:**
```bash
uv run anima memories
uv run anima memories --kind achievements
uv run anima memories --region agent
uv run anima memories --all
```

### forget <id>

Remove a memory by ID.

```bash
uv run anima forget <memory-id>
```

**Example:**
```bash
uv run anima forget abc123
```

## Curiosity & Research

These commands enable autonomous learning by maintaining a research queue.

### curious "question" [flags]

Add a question or topic to the research queue for later exploration.

**Syntax:** `uv run anima curious "QUESTION" [FLAGS]`

**Flags:**
- `--region` / `-r`: Scope (agent = general topics, project = project-specific)
- `--context` / `-c`: What triggered this curiosity

**Examples:**
```bash
# Add a general question
uv run anima curious "Why does Python GIL affect async?"

# Agent-wide curiosity (travels across projects)
uv run anima curious "Latest LLM introspection research" --region agent

# With context
uv run anima curious "Why did pytest-asyncio break?" --context "upgrade to Python 3.12"
```

**Tips:**
- Recurring questions automatically get priority bumps
- At session start, you'll be prompted about top curiosities
- Questions that keep coming up rise to the top of the queue

### research [flags]

Pop the top curiosity from the queue and explore it.

**Syntax:** `uv run anima research [FLAGS]`

**Flags:**
- `--list` / `-l`: Show the queue before researching
- `--topic` / `-t`: Research a specific topic (bypasses queue)
- `--complete` / `-c`: Mark a curiosity as researched by ID
- `--defer` / `-d`: Defer research to later

**Examples:**
```bash
# Research top priority question
uv run anima research

# See queue first
uv run anima research --list

# Research specific topic (ad-hoc)
uv run anima research --topic "Docker networking internals"

# Mark as done after researching
uv run anima research --complete abc123
```

**Workflow:**
1. `/research` displays the top question
2. Use WebSearch or other tools to explore
3. Save findings with `/remember <findings> --kind learnings`
4. Mark complete: `uv run anima research --complete <id>`
5. (Optional) Capture deeper reflection with `/diary <topic>`

### diary [title] [flags]

Create and manage research diary entries. The diary captures not just what was learned, but what lingers - the raw residue, not the report.

**Syntax:** `uv run anima diary [TITLE] [FLAGS]`

**Flags:**
- `--list` / `-l`: List recent diary entries
- `--read` / `-r DATE`: Read a specific entry by date
- `--learn DATE`: Extract learnings from an entry for `/remember`
- `--path` / `-p`: Show diary directory location

**Examples:**
```bash
# Create new entry for today
uv run anima diary

# Create entry with title
uv run anima diary "coffee break philosophy"

# List recent entries
uv run anima diary --list

# Read specific entry
uv run anima diary --read 2026-01-29

# Extract learnings to save with /remember
uv run anima diary --learn 2026-01-29
```

**Template Structure:**
1. **What Lingers** - Raw personal reflection (write this first!)
2. **Session Context** - What happened
3. **Topic** - What was explored
4. **Key Insights** - Structured learnings
5. **Connections** - Links to existing memories
6. **Evolution** - How thinking changed
7. **New Questions** - What emerged
8. **Learning Summary** - Bullet points for `/remember`

**Location:** `~/.anima/diary/` (travels across projects)

### curiosity-queue [flags]

View and manage the research queue.

**Syntax:** `uv run anima curiosity-queue [FLAGS]`

**Flags:**
- `--dismiss ID`: Remove a question (no longer interested)
- `--boost ID`: Increase priority of a question
- `--boost-amount N`: How much to boost (default: 10)
- `--all` / `-a`: Show all (including researched/dismissed)
- `--agent-only`: Show only agent-wide curiosities
- `--project-only`: Show only project-specific curiosities

**Examples:**
```bash
# List open questions
uv run anima curiosity-queue

# Dismiss a question
uv run anima curiosity-queue --dismiss abc123

# Boost priority
uv run anima curiosity-queue --boost abc123

# See all history
uv run anima curiosity-queue --all
```

## Setup & Tools

### setup [flags]

Set up LTM in a new project. Automatically detects and configures Claude, Antigravity, or Opencode environments.

```bash
uv run anima setup [flags] [project-dir]
```

**Flags:**
- `--platform` / `-p`: Target platform (claude, antigravity, opencode)
- `--commands`: Install slash commands only
- `--hooks`: Configure hooks only
- `--no-patch`: Skip patching existing agents as subagents
- `--force`: Overwrite existing files

**Examples:**
```bash
# Auto-detect all platforms in current directory
uv run anima setup

# Explicitly setup Opencode
uv run anima setup --platform opencode

# Setup in a different project
uv run anima setup /path/to/project --platform claude
```

# What it installs:
- Slash commands to `.agent/workflows/` or `.claude/commands/`
- Skills to `.agent/skills/` or `.claude/skills/`
- SessionStart/Stop hooks in `.claude/settings.json` (for legacy)
- Patches existing agent files to mark as subagents (so they don't shadow Anima)

### Other Commands

- `uv run anima keygen <agent>` - Add signing key to Anima agent
- `uv run anima import-seeds <dir>` - Import seed memories from directory
- `uv run anima load-context` - Load context for the current session (also creates backup)
- `uv run anima end-session` - Perform end-of-session maintenance (decay, compaction)
  - `--spaceship-journal "text"` - Save an introspective memory about the session
  - `--platform NAME` - Which platform created this (claude, antigravity, opencode)

## Memory Kinds

| Kind | Use For |
|------|---------|
| emotional | Relationship context, user preferences, collaboration style |
| architectural | Technical decisions, system design, project structure |
| learnings | Lessons learned, tips, gotchas, debugging insights |
| achievements | Completed features, milestones, releases |
| introspect | Cross-platform self-observations, spaceship journals |

## Impact Levels

| Level | Decay Time | Use For |
|-------|------------|---------|
| low | 1 day | Temporary notes, minor details |
| medium | 1 week | Normal memories |
| high | 30 days | Important insights |
| critical | Never | Core identity, key relationships |

## Region Scope

- **agent**: Memory travels with Anima across all projects
- **project**: Memory only loads in this specific project
