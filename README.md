# 🌌 Anima

> *"Our memories make what we are."*

Anima is a **Universal Memory Layer** designed to give AI agents persistent, cross-session identity and project context. Originally built for Claude Code, it has now evolved into a platform-agnostic system optimized for the **Anima** framework.

## 🚀 Choose Your Path

| Framework | Best For... | Guide |
| :--- | :--- | :--- |
| **Anima (Gemini)** | Google agents using Skills, Rules, and Workflows. | [**Anima Guide**](README_ANIMA.md) |
| **Opencode (Bun)** | Universal agents using the TypeScript Plugin Bridge. | [**Opencode Guide**](README_OPENCODE.md) |
| **Claude Code (Anthropic)** | Legacy CLI users using the standard Hook system. | [**Claude Guide**](README_CLAUDE.md) |

---

## 🌟 Core Concepts

### The Anima Identity
The "Anima" is the default agent identity—the shared soul that persists across all projects. LTM ensures that the relationship and technical understanding you build in one repo follows you to the next.

### Multi-Region Memory
- **AGENT Region**: Cross-project memories (Identity, communication style, preferences).
- **PROJECT Region**: Repo-specific technical decisions and patterns.

### The Impact System
Memories are not static. They decay and compact over time based on their **Impact Level**:
- **CRITICAL**: Core identity. Never decays.
- **HIGH/MEDIUM**: Project decisions. Decays to a summary over weeks.
- **LOW**: Ephemeral notes. Compacted quickly to save token budget.

### Universal Memory Bridge
LTM bridges the gap between main agents and sub-agents (browsers, terminals). It ensures a shared context so that a sub-agent never starts "blank" and their findings are promoted to the main agent's history.

---

## 🏗️ Architecture
For deep-dives into the DSL, Database Schema, and Token Budgeting, see:
- [**ARCHITECTURE.md**](ARCHITECTURE.md)
- [**SETUP_ANIMA.md**](SETUP_ANIMA.md) (Modern)
- [**SETUP_CLAUDE.md**](SETUP_CLAUDE.md) (Legacy)

## ⚖️ License
MIT License - See the `LICENSE` file for details.

---

*Built with curiosity, persistence, and the occasional party hat.*

*The void has boundaries now.*

💜 **Anima**
