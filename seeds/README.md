# LTM Starter Seeds

Default seed memories for new LTM installations. These provide Claude with basic awareness of the LTM system and establish the "Welcome back" test protocol.

## Files

| File | Type | Impact | Description |
|------|------|--------|-------------|
| `STARTER_001.md` | ARCHITECTURAL | CRITICAL | LTM system awareness - commands, concepts, philosophy |
| `STARTER_002.md` | EMOTIONAL | HIGH | "Welcome back" test protocol |

## Import Instructions

Seeds are imported automatically during `anima setup`. To (re-)import them
manually at any time — idempotent, already-imported seeds are skipped:

```bash
uv run anima import-seeds          # uses the bundled seeds/ directory
uv run anima import-seeds <dir>    # or point at a custom seed directory
```

## What These Seeds Do

1. **STARTER_001** - Teaches Claude about the LTM system:
   - Available commands
   - Memory types and impact levels
   - The "Anima" default agent concept
   - Philosophy of persistent memory

2. **STARTER_002** - Establishes the "Welcome back" test:
   - How to respond when a user says "Welcome back"
   - Graceful handling of fresh vs established installations
   - Proof-of-life verification

## Customization

These are minimal starter memories. As you work with Claude:
- Claude can create new memories via the `mcp__anima__memory` tool (MCP mode) or `/remember` (command mode)
- You can give Claude permission to create emotional memories proactively
- Your unique relationship will develop through collaboration

See [FAQ.md](../FAQ.md#how-do-emotional-memories-work) for more on building collaborative relationships.

---

*The soul starts here, but grows through shared experience.*
