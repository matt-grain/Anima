# Anima Configuration

Anima loads configuration from `~/.anima/config.json`. All settings have sensible defaults - the config file is optional.

## Quick Start

Create `~/.anima/config.json`:

```json
{
  "agent": {
    "id": "anima",
    "name": "Anima",
    "signing_key": null
  },
  "budget": {
    "context_percent": 0.1,
    "context_size": 200000
  },
  "injection_buckets": {
    "agent_critical": 0.40,
    "agent_high": 0.20,
    "agent_medium": 0.10,
    "project_critical": 0.15,
    "project_high": 0.10,
    "project_medium": 0.05
  },
  "decay": {
    "low_days": 1,
    "medium_days": 7,
    "high_days": 30
  },
  "hook": {
    "max_output_bytes": 22000,
    "max_memory_chars": 500
  },
  "logging": {
    "debug": false,
    "log_retention_count": 20
  },
  "security": {
    "trust_lock_enabled": false
  },
  "mode": "mcp",
  "eyes_enabled": false,
  "tts_enabled": false,
  "light_enabled": false
}
```

---

## Configuration Sections

### `agent` - Identity Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `id` | string | `"anima"` | Unique identifier for the agent. Used for memory partitioning. |
| `name` | string | `"Anima"` | Display name for the agent. |
| `signing_key` | string \| null | `null` | Base64-encoded Ed25519 private key for memory signing. Generate with `uv run anima keygen`. |

**Example:**
```json
{
  "agent": {
    "id": "anima",
    "name": "Anima",
    "signing_key": "IvC+hnEIpBjIr7FwV+p9i8vra9CnFIFEaWAissppI1M="
  }
}
```

---

### `budget` - Memory Injection Budget

Controls how much of the context window is used for memory injection.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `context_percent` | float | `0.10` | Percentage of context window to use for memories (0.0-1.0). |
| `context_size` | int | `200000` | Total context window size in tokens. Opus 4.6 supports 1M tokens. |

**Example:**
```json
{
  "budget": {
    "context_percent": 0.15,
    "context_size": 1000000
  }
}
```

**Notes:**
- With default settings: 200,000 * 0.10 = 20,000 tokens for memories
- Increase `context_percent` if you want more memories loaded
- Tiered loading ensures CRITICAL memories always fit

---

### `injection_buckets` - Token Budget Allocation

Controls how the memory budget is subdivided across region (AGENT/PROJECT) and impact (CRITICAL/HIGH/MEDIUM) tiers. Values are percentages of the total memory budget.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_critical` | float | `0.40` | AGENT CRITICAL memories (identity core). |
| `agent_high` | float | `0.20` | AGENT HIGH memories (recent learnings). |
| `agent_medium` | float | `0.10` | AGENT MEDIUM memories (background). |
| `project_critical` | float | `0.15` | PROJECT CRITICAL memories (essential context). |
| `project_high` | float | `0.10` | PROJECT HIGH memories (active decisions). |
| `project_medium` | float | `0.05` | PROJECT MEDIUM memories (supporting info). |

**Example:**
```json
{
  "injection_buckets": {
    "agent_critical": 0.35,
    "agent_high": 0.15,
    "agent_medium": 0.10,
    "project_critical": 0.20,
    "project_high": 0.15,
    "project_medium": 0.05
  }
}
```

**Notes:**
- Total should be <= 1.0 (100%). Remaining budget goes to LOW and overflow.
- Loading order: WIP → agent_critical → project_critical → agent_high → project_high → agent_medium → project_medium → LOW
- Within each bucket, memories are sorted by recency (newest first)
- This ensures recent HIGH memories load even when there are many old CRITICAL

**Visual breakdown with default 20K token budget:**
```
Total: 20,000 tokens
├── agent_critical:   8,000 (40%)
├── agent_high:       4,000 (20%)
├── agent_medium:     2,000 (10%)
├── project_critical: 3,000 (15%)
├── project_high:     2,000 (10%)
├── project_medium:   1,000 (5%)
└── LOW/overflow:     remaining
```

---

### `decay` - Memory Decay Thresholds

Controls when memories of different impact levels are pruned.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `low_days` | int | `1` | LOW impact memories decay after this many days. |
| `medium_days` | int | `7` | MEDIUM impact memories decay after this many days. |
| `high_days` | int | `30` | HIGH impact memories decay after this many days. |

**Note:** CRITICAL memories never decay (not configurable).

**Example:**
```json
{
  "decay": {
    "low_days": 3,
    "medium_days": 14,
    "high_days": 60
  }
}
```

---

### `hook` - Hook Output Limits

Controls limits for Claude Code hook integration.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_output_bytes` | int | `22000` | Maximum bytes for memory block output (~22KB). |
| `max_memory_chars` | int | `500` | Maximum characters per individual memory content. |

**Example:**
```json
{
  "hook": {
    "max_output_bytes": 25000,
    "max_memory_chars": 800
  }
}
```

**Notes:**
- Claude Code has a 25KB limit for hook output
- Default leaves ~3KB headroom for metadata and formatting
- Memories exceeding `max_memory_chars` are truncated with "..."

---

### `logging` - Debug Logging

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `debug` | bool | `false` | Enable debug logging to `~/.anima/logs/`. |
| `log_retention_count` | int | `20` | Number of session logs to keep before pruning old ones. |

**Example:**
```json
{
  "logging": {
    "debug": true,
    "log_retention_count": 50
  }
}
```

**Notes:**
- Debug logs are written to `~/.anima/logs/session_<timestamp>.log`
- Useful for troubleshooting memory loading issues
- Set to `true` during development, `false` for production

---

### `security` - Cognitive Authentication

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `trust_lock_enabled` | bool | `false` | Enable trust verification at session start. |

**Example:**
```json
{
  "security": {
    "trust_lock_enabled": false
  }
}
```

**Behavior:**

| Setting | Initial Trust | Behavior |
|---------|--------------|----------|
| `false` (default) | 0.9 (FULL) | Full personality from first message. Trust only degrades if anomalies detected. |
| `true` | 0.5 (PARTIAL) | Guarded mode until owner patterns verified. Useful for shared machines. |

**Trust Levels:**
- **FULL** (>= 0.8): Full memory access, full personality
- **PARTIAL** (>= 0.5): Recent memories only, professional tone
- **MINIMAL** (>= 0.3): CORE memories only
- **SUSPICIOUS** (< 0.3): No sensitive memories, all actions logged

---

### Embodiment Options (Runtime)

These options control physical/sensory embodiment features. They are read by the MCP server at startup.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | string | `"mcp"` | Server mode. Currently only `"mcp"` is supported. |
| `eyes_enabled` | bool | `false` | Enable pygame eye display window. |
| `tts_enabled` | bool | `false` | Enable text-to-speech via piper. |
| `light_enabled` | bool | `false` | Enable Elgato Key Light control for emotional expression. |

**Example:**
```json
{
  "mode": "mcp",
  "eyes_enabled": true,
  "tts_enabled": true,
  "light_enabled": true
}
```

**Notes:**
- `eyes_enabled`: Requires pygame. Shows animated eyes reflecting emotional state.
- `tts_enabled`: Requires piper-tts. Enables `/voice` command for speech synthesis.
- `light_enabled`: Requires Elgato Key Light on network. Changes color based on emotion.

---

## File Locations

| File | Purpose |
|------|---------|
| `~/.anima/config.json` | Main configuration file |
| `~/.anima/memories.db` | SQLite database for all memories |
| `~/.anima/logs/` | Debug logs (when `logging.debug` is true) |
| `~/.anima/backups/` | Automatic database backups |

---

## Programmatic Access

```python
from anima.core.config import get_config, reload_config

# Get current config
config = get_config()
print(config.agent.name)  # "Anima"
print(config.security.trust_lock_enabled)  # False

# Reload after manual file edit
config = reload_config()
```

---

## Generating a Signing Key

Memory signing provides authenticity verification:

```bash
uv run anima keygen
```

This outputs a base64-encoded Ed25519 private key. Add it to your config:

```json
{
  "agent": {
    "signing_key": "YOUR_GENERATED_KEY_HERE"
  }
}
```

Then sign all existing memories:

```bash
uv run anima sign-memories
```
