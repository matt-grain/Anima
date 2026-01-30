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

Search memories by content. Supports both keyword search and semantic (embedding-based) search.

**Syntax:** `uv run anima recall "QUERY" [FLAGS]`

**Flags:**
- `--full` / `-f`: Show complete memory content (default shows truncated)
- `--semantic` / `-s`: Use semantic search (embedding similarity) instead of keyword matching
- `--id`: Look up a specific memory by ID

**Examples:**
```bash
# Keyword search (default)
uv run anima recall "caching"

# Semantic search (finds conceptually related memories)
uv run anima recall "how does memory decay work" --semantic

# Full content view
uv run anima recall "user preferences" --full

# Direct ID lookup
uv run anima recall --id abc123
```

**Semantic Search Notes:**
- Uses embedding similarity (cosine distance) to find conceptually related memories
- Returns results with similarity percentage (e.g., "🎯 85%")
- Requires embeddings to be generated (run `backfill` for existing memories)

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

**Platform Detection:**
- If a single config directory exists (`.claude/`, `.agent/`, or `.opencode/`), that platform is auto-detected
- If no config directory exists, or multiple exist, you'll be prompted to choose:
  ```
  ⚠️  Platform auto-detection failed.
     No platform config directory found (.claude, .opencode, .agent)

  Which platform are you setting up?
    1. claude      (Claude Code - creates .claude/)
    2. antigravity (Google Antigravity - creates .agent/)
    3. opencode    (Opencode - creates .opencode/)
    q. Cancel

  Enter choice [1/2/3/q]:
  ```

**Examples:**
```bash
# Auto-detect platform (prompts if ambiguous)
uv run anima setup

# Explicitly setup Opencode
uv run anima setup --platform opencode

# Setup in a different project
uv run anima setup /path/to/project --platform claude
```

**What it installs:**
- Slash commands to `.agent/workflows/` or `.claude/commands/`
- Skills to `.agent/skills/` or `.claude/skills/`
- SessionStart/Stop hooks in `.claude/settings.json` (for legacy)
- Patches existing agent files to mark as subagents (so they don't shadow Anima)

### memory-graph [flags]

Visualize memory relationships, chains, and semantic links.

**Syntax:** `uv run anima memory-graph [FLAGS]`

**View Options:**
- `--all` / `-a`: Show all memories including standalone
- `--links` / `-l`: Show semantic links between memories
- `--tiers` / `-t`: Show memory tier distribution
- `--embeddings` / `-e`: Show embedding status

**Filter Options:**
- `--kind` / `-k TYPE`: Filter by kind (emotional, architectural, etc.)
- `--tier TIER`: Filter by tier (CORE, ACTIVE, CONTEXTUAL, DEEP)
- `--link-type TYPE`: Filter links by type (RELATES_TO, BUILDS_ON, etc.)
- `--top N`: Number of links to show (default: 20)

**Examples:**
```bash
# Show supersession chains
uv run anima memory-graph

# Show semantic links between memories
uv run anima memory-graph --links

# Filter links by type
uv run anima memory-graph --links --link-type RELATES_TO

# Show tier distribution
uv run anima memory-graph --tiers

# Show embedding coverage
uv run anima memory-graph --embeddings

# Filter by tier
uv run anima memory-graph --tier CORE --all
```

### backfill [flags]

Generate embeddings and assign tiers for existing memories. Required for semantic search and tiered loading to work with memories created before the Semantic Memory Layer was added.

**Syntax:** `uv run anima backfill [FLAGS]`

**Flags:**
- `--dry-run` / `-n`: Show what would be done without making changes
- `--batch-size` / `-b`: Number of memories to process at once (default: 32)
- `--skip-links`: Skip creating semantic links between memories

**Examples:**
```bash
# Preview what would be done
uv run anima backfill --dry-run

# Full backfill
uv run anima backfill

# Process in smaller batches (for low-memory systems)
uv run anima backfill --batch-size 16
```

**What it does:**
1. Generates FastEmbed embeddings (384 dimensions) for each memory
2. Assigns tiers based on impact, kind, and recency
3. Creates semantic links (RELATES_TO) between similar memories
4. Shows progress and summary statistics

### Version Management

Commands to check and update Anima.

#### version

Show the currently installed version.

```bash
uv run anima version
```

**Output:** `Anima v0.9.0`

#### check-update

Check if a newer version is available on GitHub.

```bash
uv run anima check-update
```

**Output:**
```
Current version: v0.9.0
Checking matt-grain/Anima for updates...

  New version available: v0.10.0
  Release: https://github.com/matt-grain/Anima/releases/tag/v0.10.0

  Run 'anima update' to upgrade
```

#### update

Update to the latest version from GitHub releases.

```bash
uv run anima update
```

**What it does:**
1. Fetches latest release from GitHub
2. Downloads and installs the wheel via `uv add --dev`
3. Runs `setup --force` to refresh hooks, commands, and skills

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

## Memory Tiers (Semantic Memory Layer)

The Semantic Memory Layer uses tiered loading to efficiently manage memory injection:

| Tier | Loading | Assignment Criteria |
|------|---------|-------------------|
| CORE | Always loaded | CRITICAL impact emotional memories |
| ACTIVE | Auto-loaded | Accessed within the last 7 days |
| CONTEXTUAL | Auto-loaded | Created within 30 days OR HIGH/CRITICAL impact |
| DEEP | On-demand | Older, lower-impact memories (via semantic search) |

**How Tiered Loading Works:**
1. **Session Start**: CORE, ACTIVE, and CONTEXTUAL tiers are auto-loaded within token budget
2. **DEEP Tier**: Not auto-loaded; available via `recall --semantic` when needed
3. **Budget Respect**: Memories are loaded in tier order until 10% context budget is reached

**Automatic Embedding & Linking:**
- New memories get embeddings generated automatically via `/remember`
- Similar memories are auto-linked with RELATES_TO connections
- Links show in `memory-graph` visualization
