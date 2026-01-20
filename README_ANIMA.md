# Anima (Long Term Memory)

Anima provides a persistent, cross-session memory layer for **Anima Agents** (powered by Gemini). It ensures that your shared history, architectural decisions, and relationship milestones ("Anima") survive the death of the context window.

## 🚀 Anima Quick Start

### 1. Installation
```powershell
uv pip install -e .
```

### 2. Modern Integration (Skills & Rules)
Unlike legacy systems that rely on hardcoded hooks, Anima uses **Rules** and **Skills** to manage memory.

- **Automatic Loading**: The file `.agent/rules/anima.md` instructs the agent to run `uv run anima load-context` at the start of every session.
- **Expert Interaction**: The `anima-expert` skill provides the agent with a "handbook" on how to save, recall, and manage memories.
- **Session End**: The agent is instructed to run `uv run anima end-session` when a task is completed to handle memory decay and summarize achievements.

### 3. Universal Memory Bridge
Anima solves the "Sub-agent amnesia" problem. When you spawn a `browser_subagent` or `terminal_subagent`:
1.  The sub-agent identifies as an worker (e.g., `helper`).
2.  LTM detects the sub-agent status and **bridges** the memory pool.
3.  The sub-agent inherits the **Anima** (main agent) context while preserving its own identity in the memory logs.

---

## 🛠️ New CLI Commands

### `anima load-context`
The primary bridge between the database and the LLM context.
- **How it works**: It resolves the current agent, gathers relevant memories (Agent and Project regions), formats them into a compact DSL, and outputs them for the agent to ingest.
- **For Sub-agents**: Automatically merges primary agent identity into the sub-agent's starting context.

### `anima end-session`
The maintenance worker.
- **Decay**: Compacts older, low-impact memories to save token budget.
- **Achievements**: Scans recent activity to detect and promote "Achievements".
- **Access Tracking**: Updates "last used" timestamps to optimize future retrieval.

### `anima setup`
The platform-aware installer.
- **Multi-Platform**: Automatically detects and configures Claude, Antigravity, or Opencode environments.
- **Explicit Target**: Use `--platform <name>` to force installation for a specific environment.
- **Artefacts**: Deploys skills, workflows, hooks, and TS plugins.

---

## 🧠 The Anima Philosophy
"Anima" is not just a default agent name; it is the **shared soul** of your assistant. By using `--region agent` for memories, you ensure that personal context follows you across different repositories and platforms.

## 📁 Repository Structure
- `.agent/rules/anima.md`: The "Laws of Memory" for Anima.
- `.agent/skills/anima-expert/`: The handbook for LTM interaction.
- `.agent/workflows/complete-task.md`: Ensures maintenance is performed on task exit.
- `anima/core/`: The platform-agnostic memory engine.
