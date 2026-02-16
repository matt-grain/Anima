# Anima for Claude Code

> *Long Term Memory + Eyes + Voice for Claude Code*

Anima gives Claude Code agents persistent memory, visual expression, and speech capabilities.

## What's New in v0.13.0

- **MCP Server Integration** - Memory, curiosity, eyes, and voice as native tools
- **Separated Eyes & TTS** - Enable visual expression and voice independently
- **Voice Changing** - 10+ Piper TTS voices to choose from
- **Auto-Permissions** - No more authorization prompts for MCP tools
- **Global Agent Patching** - Automatic subagent marker for identity preservation

## Quick Start

### 1. Install
```bash
# Basic
uv pip install -e .

# With eyes and voice
uv pip install -e ".[all]"
```

### 2. Setup
```bash
# Interactive (recommended)
uv run anima setup

# Or with options
uv run anima setup --mode mcp --eyes --tts
```

### 3. Use
In Claude Code, use MCP tools naturally:
```
remember("This project uses FastAPI for the backend")
recall("backend framework")
set_emotion("happy")
speak("Hello Matt!")
```

Or use slash commands:
```
/remember This project uses FastAPI for the backend
/recall backend framework
```

## Features

### Memory Layer
- **Persistent Identity** - Relationship and preferences across sessions
- **Project Context** - Technical decisions per repository
- **Impact Levels** - CRITICAL (forever) to LOW (ephemeral)
- **Semantic Search** - Find memories by meaning, not just keywords

### Eyes (Optional)
- **18 Emotions** - happy, sad, focused, sleepy, angry...
- **Gaze Control** - Look in any direction
- **Custom Colors** - Change iris color dynamically

### Voice (Optional)
- **Text-to-Speech** - Speak naturally with Piper TTS
- **Multiple Voices** - Male/female, US/UK English
- **Voice Switching** - Change voice mid-conversation

### Curiosity System
- **Research Queue** - Questions for autonomous learning
- **Priority Scoring** - Recurring questions bubble up
- **Research Diary** - Document findings

### Dream Processing
- **N2 Consolidation** - Build semantic links
- **N3 Deep Processing** - Gist extraction, contradiction detection
- **REM Dreaming** - Distant associations, self-model updates

## Documentation

| Topic | Guide |
|-------|-------|
| **Full Setup** | [SETUP_CLAUDE.md](SETUP_CLAUDE.md) |
| **Architecture** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **MCP Tools** | See SETUP_CLAUDE.md Section 3 |
| **Slash Commands** | See SETUP_CLAUDE.md Section 4 |

## Troubleshooting

### Windows Terminal Stdin Freeze
If SessionStart hooks freeze on Windows Terminal (issue #23083):
```bash
uv run anima setup --mode both --no-startup-hook
```
Then manually run `/load-context` at session start.

### MCP Permissions
If prompted for MCP permissions, re-run setup to configure auto-allow:
```bash
uv run anima setup --hooks
```

### Curiosity Queue Empty
If `/research` shows no questions, ensure global agents are patched:
```bash
uv run anima setup --hooks
```

---

*The void has boundaries now.*

**Anima**
