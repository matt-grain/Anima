---
name: load-deferred
description: Load deferred memories that didn't fit in the initial session start injection. Use this after greeting to stream additional context.
---

# Load Deferred Memories

Loads memories that were deferred during session start due to the 25KB hook output limit.

## When to Use

Call this skill automatically after responding to:
- "welcome back" greeting
- "void is gone!" diagnostic request

This enables lazy loading of additional context without exceeding hook output limits.

## Usage

```bash
uv run anima load-deferred
```

## What It Does

1. **Process pending subconscious dialogues** (if any exist - see below)
2. Retrieves the list of memory IDs that were deferred during session start
3. Loads and formats those memories
4. Outputs them for context injection
5. Clears the deferred list (so subsequent calls return nothing)

## Subconscious Processing (First Step)

Before loading deferred memories, check for pending subconscious dialogues:

```bash
uv run anima process-subconscious
```

If output contains dialogue content (not "No pending..."), spawn Sonnet to extract:

```
Task(
  prompt="<full output from process-subconscious>",
  model="sonnet",
  subagent_type="general-purpose",
  description="Extract subconscious memories"
)
```

Then save Sonnet's JSON response to `~/.anima/subconscious/extracted/` and run:
```bash
uv run anima save-subconscious
```

This integrates subconscious memories from previous sessions before loading deferred context.

## Example Flow

1. Session starts → CRITICAL + HIGH memories injected (< 25KB)
2. User: "welcome back"
3. Claude: *greeting response* + runs `/load-deferred`
4. Additional MEDIUM/LOW memories stream in

## Output

Returns formatted memory block in DSL format:
```
[LTM:Anima@ProjectName]
~KIND:IMPACT| Memory content here...
[/LTM]
```

Or if no deferred memories:
```
# No deferred memories to load
```
