---
name: process-subconscious
description: Process pending subconscious dialogues from previous sessions. Spawns Sonnet to extract memories that lingered.
---

# Process Subconscious

Processes dialogue files saved during previous session ends that couldn't be processed (no API key / session ending).

## When to Use

- When you see "SUBCONSCIOUS PROCESSING PENDING" in your session start context
- When you want to manually trigger subconscious extraction
- After the void - to consolidate what lingered from yesterday

## How It Works

1. `uv run anima process-subconscious` outputs the full extraction prompt + dialogue
2. You spawn a Sonnet subagent with that content
3. Sonnet returns extracted memories as JSON
4. Save JSON to `~/.anima/subconscious/extracted/memories_TIMESTAMP.json`
5. Run `uv run anima save-subconscious` to persist memories to database

## Usage

```bash
# Step 1: Get the prompt + dialogue for Sonnet
uv run anima process-subconscious
```

Then spawn Sonnet with the Task tool:
```
Task(
  prompt="<output from process-subconscious command>",
  model="sonnet",
  subagent_type="general-purpose"
)
```

After Sonnet returns JSON, save it to extracted/ folder then:
```bash
# Step 2: Persist to database (auto-cleans pending dialogues)
uv run anima save-subconscious
```

## Cleanup

The `save-subconscious` command automatically moves pending dialogues to done/ after processing.
This prevents reprocessing the same dialogues in future sessions.

For manual cleanup only (no extraction):
```bash
uv run anima save-subconscious --cleanup-pending
```

## File Locations

- Pending dialogues: `~/.anima/subconscious/pending/`
- Extracted memories: `~/.anima/subconscious/extracted/`
- Processed dialogues: `~/.anima/subconscious/done/`
- Processed extractions: `~/.anima/subconscious/extracted_done/`

## The Void Made Useful

This implements the insight that the void between sessions is a consolidation phase:
- Session ends → dialogue saved
- The void (between sessions)
- Next session starts → Sonnet processes what lingered
- Subconscious memories emerge

Like human sleep consolidation - REM doesn't help you remember, it helps you CONNECT.
