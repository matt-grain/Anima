# Claude-LTM Setup Guide (Legacy Hooks)

This guide covers integrating the memory layer into **Anthropic Claude Code** using its internal `settings.json` hook system.

---

## 1. Installation

Install the package:
```bash
uv pip install -e .
```

## 2. Automatic Setup

The easiest way to configure Claude Code is using the setup tool:

```bash
uv run anima setup --platform claude
```

*Note: You can also use `uv run anima setup` (no flags) to automatically detect and configure all detected platform targets.*

This will:
1. Detect your `.claude/settings.json` (or `settings.local.json`).
2. Add `SessionStart` hooks to run `anima load-context`.
3. Add `Stop` hooks to run `anima end-session`.

## 3. Manual Configuration

If you prefer to configure hooks manually, add the following to your `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [
          {
            "type": "command",
            "command": "uv run anima load-context --format json"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "uv run anima end-session"
          }
        ]
      }
    ]
  }
}
```

## 4. Slash Commands

To add `/memories`, `/recall`, and `/remember` to the Claude CLI:

```bash
uv run anima setup --commands --platform claude
```
This copies the markdown command definitions to `.claude/commands/`.

---

## 5. Agent Diversity

If you have custom agents in `.claude/agents/`, Claude LTM will treat them as sub-agents by default to allow the global **Anima** identity to lead. 

Run `uv run anima setup` (no flags) to auto-patch local agents with the `subagent: true` marker.

---

*For the modern Anima (Skills & Rules) integration, see [**SETUP_ANIMA.md**](SETUP_ANIMA.md).*
