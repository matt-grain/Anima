# LTM for Claude Code (Legacy Support)

This guide covers the integration of the Long Term Memory (LTM) system into the **Anthropic Claude Code** CLI.

## 🚀 Claude Quick Start

### 1. Installation
```bash
uv pip install -e .
```

### 2. Hook Integration
Claude Code relies on a `settings.json` hook system to inject memories.

- **Setup**: Run `uv run python -m ltm.tools.setup`.
- **Function**: This tool will:
    1. Patch your `.claude/settings.json` to add `SessionStart` and `SessionStop` hooks.
    2. Point those hooks to `ltm/hooks/session_start.py` and `session_end.py`.
    3. Install legacy command files in `.claude/commands/`.

### 3. Memory Injection
In Claude Code, memories are injected as a JSON block via the hook system. The agent sees a specific message at the start of every session containing the [LTM] block.

---

## 🛠️ Commands

Claude-LTM supports standard slash commands:
- `/remember`: Save a memory.
- `/recall`: Search memories.
- `/memories`: List all long-term context.

## 📁 Repository Structure
- `.claude/settings.json`: Configuration for hooks.
- `ltm/hooks/`: Python logic for JSON-based injection.
- `ltm/commands/`: Command implementations.

---

*Note: While fully supported, new features like the Universal Memory Bridge are optimized for the Anima Agent framework. We recommend migrating to Anima for the full experience.*
