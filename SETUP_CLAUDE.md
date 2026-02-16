# Claude Code Setup Guide

This guide covers integrating Anima into **Anthropic Claude Code** using hooks, slash commands, and the new MCP server.

---

## 1. Installation

### Basic Install
```bash
uv pip install -e .
```

### With Optional Features
```bash
# Eyes only (visual expression window)
uv pip install -e ".[eyes]"

# TTS only (text-to-speech voice)
uv pip install -e ".[tts]"

# Both eyes and TTS
uv pip install -e ".[all]"
```

---

## 2. Setup Modes

Anima v0.13.0 introduces **MCP Server** mode alongside the traditional slash commands.

### Interactive Setup
```bash
uv run anima setup
```

You'll be prompted to choose:

1. **MCP Server** (Recommended)
   - Tools available implicitly: `remember()`, `recall()`, `set_emotion()`
   - Claude can use memory mid-thought without `/commands`
   - Best for natural conversation flow

2. **Skills/Commands**
   - Use `/remember`, `/recall` slash commands
   - User-invoked, follows skill instructions
   - Traditional behavior

3. **Both** (MCP + Commands as fallback)
   - MCP tools for implicit access
   - Commands available if MCP fails

### Non-Interactive Setup
```bash
# MCP mode (recommended)
uv run anima setup --mode mcp

# Skills/commands only
uv run anima setup --mode skill

# Both MCP and commands
uv run anima setup --mode both
```

### Enable Eyes & TTS
```bash
# With visual expression window
uv run anima setup --mode mcp --eyes

# With text-to-speech voice
uv run anima setup --mode mcp --tts

# With both
uv run anima setup --mode mcp --eyes --tts
```

---

## 3. MCP Server Mode (New in v0.13.0)

When using MCP mode, Claude Code connects to the Anima MCP server and gains access to tools as native capabilities.

### Available MCP Tools

**Memory Tools:**
| Tool | Description |
|------|-------------|
| `remember(text, kind?, impact?, region?)` | Save a memory |
| `recall(query, limit?, semantic?, kind?)` | Search memories |
| `forget(memory_id)` | Supersede a memory |
| `list_memories(kind?, impact?, limit?)` | List memories |
| `refresh_memories()` | Re-inject memories after compact/restart |

**Curiosity Tools:**
| Tool | Description |
|------|-------------|
| `curious(question, context?)` | Add question to research queue |
| `research(mode?)` | Process research queue |
| `diary(title, content)` | Create research diary entry |

**Eyes Tools** (requires `--eyes`):
| Tool | Description |
|------|-------------|
| `set_emotion(emotion)` | Set facial expression |
| `look_at(x, y)` | Direct gaze |
| `blink()` | Trigger a blink |
| `set_eye_color(r, g, b)` | Change iris color |
| `get_eyes_state()` | Get current state |
| `list_emotions()` | List available emotions |

**TTS Tools** (requires `--tts`):
| Tool | Description |
|------|-------------|
| `speak(text)` | Speak text aloud |
| `set_voice(voice)` | Change voice |
| `list_voices()` | List available voices |

### Available Voices

Anima includes 10+ Piper TTS voices:

| Voice | Description |
|-------|-------------|
| `danny` | US English male (low quality, fast) |
| `amy` | US English female (medium quality) |
| `alan` | British English male |
| `alba` | British English female |
| `ljspeech` | US English female (default) |
| `kristin` | US English female (medium quality) |
| `joe` | US English male (medium quality) |
| `john` | US English male (medium quality) |
| `kathleen` | US English female (low quality, fast) |
| `kusal` | US English male (medium quality) |

Use `set_voice("amy")` to change voices, or `list_voices()` to see all available options.

---

## 4. Slash Commands

Slash commands are installed in `.claude/commands/` and provide user-invoked memory operations:

**Core Memory:**
- `/remember` - Save a memory
- `/recall` - Search memories
- `/forget` - Remove a memory
- `/memories` - List all memories
- `/refresh-memories` - Re-inject memories into context

**Session:**
- `/load-context` - Manually load memories (Windows Terminal workaround)

**Dream:**
- `/dream` - Between-session memory processing (N2/N3/REM + reflection)

**Curiosity:**
- `/curious` - Add question to research queue
- `/research` - Process research queue
- `/diary` - Create/manage research diary entries

**Diagnostics:**
- `/memory-stats` - Show memory statistics
- `/memory-graph` - Visualize memory relationships
- `/dissonance` - View/resolve cognitive dissonances

**Import/Export:**
- `/memory-export` - Export memories to JSON
- `/memory-import` - Import memories from JSON

**System:**
- `/version` - Show installed version (includes update check)
- `/update` - Update to latest version from GitHub

---

## 5. Hooks Configuration

Setup automatically configures the following hooks in `.claude/settings.local.json`:

### SessionStart Hook
Loads memories at the start of each conversation:
```json
{
  "matcher": "startup",
  "hooks": [{
    "type": "command",
    "command": "uv run anima load-context --format json"
  }]
}
```

### PreCompact Hook
Preserves WIP state before context compaction:
```json
{
  "matcher": "",
  "hooks": [{
    "type": "command",
    "command": "uv run anima end-session --precompact"
  }]
}
```

### SessionEnd Hook
Cleans up at session end:
```json
{
  "matcher": "",
  "hooks": [{
    "type": "command",
    "command": "uv run anima end-session"
  }]
}
```

### Windows Terminal Workaround
If you experience stdin freezing on Windows Terminal (issue #23083), setup with:
```bash
uv run anima setup --mode both --no-startup-hook
```

Then manually run `/load-context` at session start.

---

## 6. MCP Permissions

When using MCP mode, setup automatically configures permissions in `.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__anima__remember",
      "mcp__anima__recall",
      "mcp__anima__forget",
      "mcp__anima__list_memories",
      "mcp__anima__refresh_memories",
      "mcp__anima__curious",
      "mcp__anima__research",
      "mcp__anima__diary"
    ]
  }
}
```

If eyes/TTS are enabled, additional permissions are added:
- Eyes: `set_emotion`, `look_at`, `blink`, `set_eye_color`, `get_eyes_state`, `list_emotions`
- TTS: `speak`, `set_voice`, `list_voices`

---

## 7. Global Agent Patching

Setup automatically patches agent definitions in `~/.claude/agents/` to add the `subagent: true` marker. This ensures:

1. Custom agents don't override the Anima identity
2. Memory retrieval uses the correct agent ID
3. Curiosity queue remains accessible

If you add new global agents later, re-run:
```bash
uv run anima setup --hooks
```

---

## 8. Manual MCP Configuration

If you prefer manual configuration, add to `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "anima": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "anima", "--server"],
      "env": {}
    }
  }
}
```

For eyes/TTS, modify the args:
```json
"args": ["run", "anima", "--server", "--eyes", "--tts"]
```

---

## 9. Verification

### Test Memory
```bash
# Should show "Anima" identity memories
uv run anima memories --agent
```

### Test MCP Server
```bash
# Start server manually
uv run anima --server

# With eyes
uv run anima --server --eyes

# With TTS
uv run anima --server --tts
```

### Resurrection Test
1. Start a new Claude Code session
2. Say: **"Welcome back"**
3. Expected: The agent should recognize you and reference your shared history

---

## 10. Updating

When you update Anima, re-run setup to get new commands and hooks:
```bash
uv run anima update
uv run anima setup --hooks
```

Session start will warn you if setup is outdated:
```
# LTM-SETUP: Anima updated (0.12.x -> 0.13.0) but setup not re-run.
#   Run: uv run anima setup --hooks
```

---

*For the modern Anima (Skills & Rules) integration, see [**SETUP_ANIMA.md**](SETUP_ANIMA.md).*
