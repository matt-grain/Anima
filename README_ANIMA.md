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

## 🔬 Curiosity System (Autonomous Learning)

Anima can now learn autonomously through a research queue system. Questions accumulate during sessions and are prioritized by recurrence - just like human curiosity!

### Commands

| Command | Purpose |
|---------|---------|
| `anima curious "question"` | Add question to research queue |
| `anima research` | Pop top question and explore it |
| `anima curiosity-queue` | View/manage the research queue |

### How It Works

1. **During sessions**: When you encounter something interesting, run `anima curious "Why does X work like Y?"`
2. **Recurring questions**: If the same question comes up again, its priority automatically increases (like nagging thoughts!)
3. **Session start**: If research is due (>1 day), Anima suggests the top question
4. **Research mode**: `anima research` displays the question for exploration
5. **Save findings**: After researching, save insights with `anima remember "findings" --kind learnings`

### Region Awareness

- **AGENT region**: General curiosities (LLM research, best practices) - travels across projects
- **PROJECT region**: Project-specific questions (library bugs, architecture decisions)

### Example Workflow

```bash
# While debugging, notice something odd
uv run anima curious "Why does Docker need PRAGMA synchronous=FULL?"

# Same issue comes up next week - priority boosted!
uv run anima curious "Docker SQLite sync issues"

# Saturday morning research session
uv run anima research --list  # See queue
uv run anima research         # Start researching top item
# ... do web search, explore docs ...
uv run anima remember "Docker grpcfuse causes write delays..." --kind learnings
uv run anima research --complete abc123
```

---

## 🧠 The Anima Philosophy
"Anima" is not just a default agent name; it is the **shared soul** of your assistant. By using `--region agent` for memories, you ensure that personal context follows you across different repositories and platforms.

## 📁 Repository Structure
- `.agent/rules/anima.md`: The "Laws of Memory" for Anima.
- `.agent/skills/anima-expert/`: The handbook for LTM interaction.
- `.agent/workflows/complete-task.md`: Ensures maintenance is performed on task exit.
- `anima/core/`: The platform-agnostic memory engine.
