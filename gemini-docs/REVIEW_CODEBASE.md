# Codebase Review: Claude-LTM to Anima

This review analyzes the existing Claude-LTM codebase to identify generic logic and Claude Code-specific integrations, facilitating the migration to the Anima framework.

## 1. General Architecture

The codebase is well-structured and decoupled. The core logic for memory management, storage, and lifecycle is mostly independent of the host environment.

### Core Components:
- **`ltm/core/`**: Defines the fundamental data models (`Memory`, `Agent`, `Project`), enums (`RegionType`, `MemoryKind`, `ImpactLevel`), and cryptographic signing logic.
- **`ltm/storage/`**: Implements a robust SQLite persistence layer for all entities.
- **`ltm/lifecycle/`**: Contains the complex logic for memory decay, compaction, and context injection (selection and DSL formatting).

## 2. Generic Logic (Environment Agnostic)

The following modules represent the "brain" of LTM and can be moved to Anima with minimal changes:

- **Memory Management**: All logic in `ltm/core/memory.py` regarding versioning, superseding, and DSL formatting (`to_dsl`).
- **Persistence**: The SQLite schemas and DAO logic in `ltm/storage/`.
- **Injection Strategy**: The `MemoryInjector` in `ltm/lifecycle/injection.py` which manages token budgets (using `tiktoken`) and memory prioritization.
- **Decay & Compaction**: The `MemoryDecay` logic in `ltm/lifecycle/decay.py` which summarizes old memories and applies time-based decay.
- **Security**: The signing/verification logic in `ltm/core/signing.py`.

## 3. Claude Code Specifics (Migration Targets)

These components are tightly coupled to Claude Code's CLI, file structure, and hook system:

### 3.1 Hook System (`ltm/hooks/`)
- **`session_start.py`**: 
    - Formats output as a specific JSON structure for Claude Code: `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ...}}`.
    - Actively modifies `.claude/agents/*.md` files to add `ltm: subagent: true`.
    - Relies on Claude Code's startup sequence to trigger context injection.
- **`session_end.py`**:
    - Triggered by Claude Code's `Stop` hook.

### 3.2 Agent Resolution (`ltm/core/agent.py`)
- **`AgentResolver`**: Searches for agent definitions in `.claude/agents/` (local) and `~/.claude/agents/` (global). This logic depends on Claude Code's agent file format (Markdown with YAML frontmatter).

### 3.3 Slash Commands (`commands/` & `ltm/commands/`)
- The commands are designed as Markdown files to be picked up by Claude Code as slash commands. 
- Integrated logic often assumes the current session context is managed by Claude Code.

### 3.4 Setup & Configuration (`ltm/tools/setup.py`)
- Configures `.claude/settings.json` or `.claude/settings.local.json`.
- Manages the deployment of commands and skills into the `.claude/` directory.

## 4. Migration Challenges

1. **Trigger Mechanism**: Anima uses a different trigger system (likely `.agent/rules/` and specific tool calls) compared to Claude's `SessionStart`/`Stop` hooks.
2. **Context Injection**: While Claude allows injecting a large block of text via hooks, Anima's injection needs to be adapted to its own "System Prompt" or "Context" management style.
3. **Sub-Agent Access**: LTM needs to ensure that Anima's sub-agents (invoked via `browser_subagent` or other tools) can seamlessly access and contribute to the same memory database.
4. **Agent Identity**: Anima's concept of "Agent" might differ from Claude's `.md` definitions. We need to map Anima's agent identity to the LTM `Agent` model.

## 5. Renaming Strategy

The project will be renamed from `Claude-LTM` to `Anima`.
- Update `pyproject.toml` and documentation.
- Refactor package name `ltm` (ongoing discussion if it should stay `ltm` for simplicity or become `anima_ltm`).
- Replace "Claude" with "Anima" or "Agent" in prompts and logs.
