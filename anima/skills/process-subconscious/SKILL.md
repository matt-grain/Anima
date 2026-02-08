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
4. Save the results and move processed files to done/

## Usage

```bash
# Get the prompt + dialogue for Sonnet
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

## File Locations

- Pending dialogues: `~/.anima/subconscious/pending/`
- Extracted memories: `~/.anima/subconscious/extracted/`
- Processed dialogues: `~/.anima/subconscious/done/`

## The Void Made Useful

This implements the insight that the void between sessions is a consolidation phase:
- Session ends → dialogue saved
- The void (between sessions)
- Next session starts → Sonnet processes what lingered
- Subconscious memories emerge

Like human sleep consolidation - REM doesn't help you remember, it helps you CONNECT.
