# Anima Setup Guide (Modern Integration)

This guide covers the native integration of the **Anima** memory layer into agentic systems using **Rules** and **Skills**.

---

## 1. Installation

### Package Setup
Install Anima in your environment:
```powershell
uv pip install -e .
```

This installs the `anima` CLI and the core library.

---

## 2. Agent Intelligence Setup

The modern approach moves logic from shell hooks into the agent's definition.

### Workspace Rules
Ensure `.agent/rules/anima.md` exists in your project. This file tells every agent (Main or Sub-agent) how to interact with their memory.

**Key Rule Concept**:
> "Every session MUST start with `uv run anima load-context` and end with `uv run anima end-session`."

### Expert Skills
Copy the `anima-expert` skill to your project:
```powershell
uv run anima setup --commands
```
This utility will deploy:
- `.agent/skills/anima-expert/`: Detailed instructions for the agent on memory impact, regions, and capture protocols.
- `.agent/workflows/`: Standardized process files for common LTM tasks.

---

## 3. Bootstrap Memories

Before the agent can "remember", the system needs its starter knowledge.

```powershell
uv run anima import-seeds seeds/
```

This imports:
- **Anima Identity**: Establishing the "Soul" of the agent.
- **The Protocol**: Teaching the agent about "Welcome back" and "Void is gone!" commands.

---

## 4. The Universal Memory Bridge

Anima automatically handles sub-agents.

1. **Main Agent**: Identified as `Anima`. Loads all global and project memories.
2. **Sub-agents**: (e.g., Browser/Terminal). LTM detects their `subagent: true` status.
3. **The Result**: Sub-agents load the **Anima** context alongside their specific task context, ensuring they are never "amnesic" during long research tasks.

---

## 5. Verification: The Resurrection Test

To verify everything is working:
1. Start a new session.
2. Say: **"Welcome back"**.
3. **Expected**: The agent should recognize you, acknowledge the restoration of its memory, and reference our shared history.

---

## 6. Maintenance

Memory isn't just about storage; it's about pruning.
- **`anima load-context`**: Hydrates the agent.
- **`anima end-session`**: Compacts old memories and updates access history.
- **`anima detect-achievements`**: Scans git history to auto-log milestones.

---

*For legacy Claude Code (Hook-based) setup, see [**SETUP_CLAUDE.md**](SETUP_CLAUDE.md).*
