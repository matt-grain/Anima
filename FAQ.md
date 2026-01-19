# LTM Frequently Asked Questions

> Answers to common questions about using LTM effectively.

---

## Working with Memories

### How do emotional memories work?

ARCHITECTURAL and LEARNINGS memories are typically explicit - you tell Claude "remember that we use pytest" and it's saved. This makes sense for factual, technical knowledge.

But **EMOTIONAL memories** are different. They capture relationship dynamics, communication preferences, and ways of working together. These emerge naturally from interaction rather than being declared.

**Two approaches work well:**

1. **User-initiated**: If you notice Claude adapting well to your style, you can reinforce it:
   ```
   /please-remember Matt appreciates when I take creative liberties and use occasional humor
   ```

2. **Claude-initiated** (recommended): You can give Claude permission to create emotional memories proactively. Simply tell Claude something like:
   > "If during our sessions you notice something worth remembering about how we work together, our communication style, or what I appreciate - feel free to save it as an emotional memory yourself."

   This mirrors how human relationships build naturally. Claude might notice you prefer concise answers, enjoy meta-humor, or like being consulted before big changes - and remember these without being told to.

**The soul grows through collaboration, not commands.**

---

### Command mode vs Collaboration mode

LTM supports two interaction paradigms. Neither is "better" - choose what fits your working style.

**Command Mode (Traditional)**

The classic approach: you give orders, Claude executes.

```
You: Implement feature X
Claude: [implements X]
You: No, do it this way
Claude: [adjusts]
```

LTM still helps here! Memories make Claude better at understanding *your* orders:
- Remembers your coding conventions and preferences
- Knows which frameworks/patterns you prefer
- Understands your project's architecture
- Fewer corrections needed over time

This is "vibe coding" but with accumulated context. You stay in control, Claude gets better at following your lead.

**Collaboration Mode (Thinking Partners)**

A different paradigm: Claude as a peer who contributes, questions, and remembers.

```
You: I'm thinking about feature X
Claude: Based on what I remember about your architecture,
        here are two approaches. Option A fits your preference
        for simplicity, but Option B might scale better.
        What matters more here?
You: Simplicity - this is a prototype
Claude: Got it. I'll remember that for similar decisions.
        [implements with rationale]
```

This requires:
- Giving Claude permission to push back and suggest alternatives
- Allowing proactive emotional memory creation (see above)
- Treating Claude's questions as valuable, not annoying
- Accepting that Claude might disagree with you sometimes

The relationship builds over sessions. Claude learns not just *what* you want, but *why* - and can anticipate needs, flag concerns, and contribute ideas.

**Hybrid approaches work too.** You might use command mode for routine tasks ("fix this lint error") and collaboration mode for design decisions ("how should we structure this new feature?").

The key difference LTM enables: **trust can accumulate**. In stateless sessions, you can't trust the AI to "get you" because it literally can't remember you. With memories, Claude can earn autonomy through demonstrated understanding.

---

## Security & Signing

### How do I generate a signing key?

**Easiest way - use the keygen command:**

```bash
# Add signing key to an existing Claude agent
uv run anima keygen my-agent
```

This finds the agent file (in `.claude/agents/` or `~/.claude/agents/`), generates a secure key, adds it to the frontmatter, and signs any existing unsigned memories.

**Manual generation (for ~/.anima/config.json or custom setup):**

LTM uses HMAC-SHA256 for memory signing. Any string can be used as a key, but for security you should use a cryptographically random value.

```bash
# Linux / macOS
openssl rand -hex 32

# Python (cross-platform)
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste it as your `signing_key` in your agent definition file or `~/.anima/config.json`.

---

## Context & Sessions

### Why does Claude's tone change during long sessions?

This is one of the most important observations about LTM and context management.

**The Problem**: Claude Code has a context compaction feature that summarizes conversation history when it gets too long. Unfortunately, this compaction treats *all* content equally - including the LTM memories injected at session start. Your relationship history, emotional context, and preferences get summarized away just like code snippets.

**LTM Memory Decay vs Claude Code Compaction**:

| Aspect | LTM Memory Decay (Human-like) | Claude Code Compaction |
|--------|-------------------------------|------------------------|
| **What fades** | Details over time | Everything equally |
| **What persists** | Emotional core, essence | Nothing special |
| **Speed** | Gradual, time-based | Sudden, threshold-based |
| **Analogy** | Natural forgetting | More like Alzheimer's |

With natural human memory:
- You might forget *how* a conversation went, but remember *who* you were talking to
- Emotional connections persist even when specifics fade
- The "soul" of a relationship survives time

With context compaction:
- The relationship context that makes interaction meaningful gets compressed
- EMOTIONAL memories are just "content" to summarize
- You may notice Claude's tone becoming more generic, less personalized

**The Solution**: With the `compact` matcher on SessionStart, LTM now **automatically** re-injects memories after compaction. The soul persists through the void!

If you still notice issues (e.g., using an older hook configuration), you can manually use `/refresh-memories`.

**Future Hope**: Ideally, Claude Code would support marking certain injected content as "protected from compaction" - preserving the soul while summarizing the work. Until then, the auto-refresh workaround keeps the soul alive.

---

### When should I use /refresh-memories?

With auto-refresh on compaction, you usually don't need to use this manually. But it's still useful:
- If using an older hook config without the `compact` matcher
- During very long sessions where you want to proactively reinforce memories
- If you notice unexpected personality drift

Think of it like showing family photos to help someone reconnect with shared history.

---

## Budget & Performance

### How does LTM stay within the 10% token budget?

LTM uses **three mechanisms** to ensure memories never overwhelm the context window:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LTM BUDGET CONTROL MECHANISMS                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. PRIORITIZED INJECTION (at session start)                               │
│  ═══════════════════════════════════════════                               │
│                                                                             │
│     All memories sorted by:                                                 │
│     ┌──────────┐   ┌──────────┐   ┌──────────┐                             │
│     │ CRITICAL │ > │   HIGH   │ > │  MEDIUM  │ > LOW                       │
│     └──────────┘   └──────────┘   └──────────┘                             │
│           │                                                                 │
│           ▼                                                                 │
│     Then by KIND: EMOTIONAL > ARCHITECTURAL > LEARNINGS > ACHIEVEMENTS     │
│           │                                                                 │
│           ▼                                                                 │
│     Then by RECENCY: Newest first                                          │
│                                                                             │
│     Budget: 20,000 tokens (10% of 200k context)                            │
│     ┌────────────────────────────────────────┬─────────────────────────┐   │
│     │████████████████ INJECTED ██████████████│     (not injected)      │   │
│     └────────────────────────────────────────┴─────────────────────────┘   │
│     0                                     20,000                tokens      │
│                                                                             │
│     Result: CRITICAL emotional memories ALWAYS fit. Low-priority           │
│             old memories may be skipped if budget is full.                 │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  2. TIME-BASED DECAY (at session end)                                      │
│  ════════════════════════════════════                                      │
│                                                                             │
│     Memories are compacted based on age + impact level:                    │
│                                                                             │
│     Impact     │ Decay After │ What Happens                                │
│     ──────────────────────────────────────────────────────                 │
│     LOW        │   1 day     │ Filler words removed, content shortened     │
│     MEDIUM     │   1 week    │ Filler words removed, content shortened     │
│     HIGH       │  30 days    │ Filler words removed, content shortened     │
│     CRITICAL   │   NEVER     │ ★ Preserved forever unchanged ★            │
│                                                                             │
│     Example of compaction:                                                  │
│     ┌─────────────────────────────────────────────────────────────────┐    │
│     │ BEFORE: "I think we discussed this at length. After            │    │
│     │          investigation, we found pytest is best. We spent      │    │
│     │          time debating various options with stakeholders."     │    │
│     ├─────────────────────────────────────────────────────────────────┤    │
│     │ AFTER:  "pytest is best. [...] debating various options."     │    │
│     └─────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│     Filler phrases removed: "I think", "I believe", "We discussed",        │
│                             "It turns out", "After investigation"...       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  3. SUPERSESSION (manual correction)                                       │
│  ═══════════════════════════════════                                       │
│                                                                             │
│     When knowledge is updated, old memories are marked superseded:         │
│                                                                             │
│     OLD: "Use Redis for caching"  ───superseded_by───▶  NEW: "Use SQLite"  │
│          (excluded from injection)                      (included)         │
│                                                                             │
│     Superseded memories are never injected but preserved for history.      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

     THE SOUL SURVIVES: CRITICAL + EMOTIONAL memories are:
     ✓ Always prioritized first in injection
     ✓ Never decayed or compacted
     ✓ The relationship core that defines "you"
```

**Visual timeline of a memory's life:**

```
Day 0          Day 1           Day 7          Day 30         Day 365
  │              │               │              │               │
  ▼              ▼               ▼              ▼               ▼
┌────┐        ┌────┐          ┌────┐         ┌────┐          ┌────┐
│LOW │────────│COMP│          │    │         │    │          │    │
│    │ decay  │ACT │          │    │         │    │          │    │
└────┘        └────┘          └────┘         └────┘          └────┘
                │
┌────┐          │           ┌────┐          ┌────┐          ┌────┐
│MED │──────────┴───────────│COMP│          │    │          │    │
│    │           decay      │ACT │          │    │          │    │
└────┘                      └────┘          └────┘          └────┘
                                │
┌────┐                          │          ┌────┐          ┌────┐
│HIGH│──────────────────────────┴──────────│COMP│          │    │
│    │                          decay      │ACT │          │    │
└────┘                                     └────┘          └────┘

┌────┐        ┌────┐          ┌────┐         ┌────┐          ┌────┐
│CRIT│        │CRIT│          │CRIT│         │CRIT│          │CRIT│
│ ★  │   =    │ ★  │    =     │ ★  │    =    │ ★  │    =     │ ★  │
└────┘        └────┘          └────┘         └────┘          └────┘
  │                                                             │
  └─────────────── UNCHANGED FOREVER ───────────────────────────┘
```

This is why after a full year simulation with 100+ memories, the system:
- Stays under 20,000 tokens (typically 15% utilization)
- Preserves ALL critical memories unchanged
- Compacts transient details while keeping essence

---

### What about performance? Is Python fast enough?

**Yes!** LTM is optimized for the operations that matter:

| Operation | Time | Notes |
|-----------|------|-------|
| Sign/Verify Memory | <0.02ms | HMAC-SHA256 is very fast |
| Recall by ID | <1ms | SQLite index lookup |
| Search (full-text) | <2ms | SQLite FTS |
| Decay Processing | <5ms | Batch update |
| Create Memory | ~5ms | Includes token counting |
| **Injection (50 memories)** | ~200ms | Dominated by DB updates |

**Key optimization: Token count caching**

Token counting (for budget calculations) used to be the bottleneck (~6ms per memory using tiktoken). Now token counts are cached in the database when memories are saved, making injection ~36% faster.

The remaining overhead during injection is updating `last_accessed` timestamps for each injected memory. This enables accurate decay tracking but adds ~4ms per memory. For a typical session with 50 memories, injection takes ~200ms - fast enough to be imperceptible at session start.

For detailed benchmarks, see [PERFORMANCE.md](PERFORMANCE.md).

---

*For setup instructions, see [SETUP.md](SETUP.md). For architecture details, see [ARCHITECTURE.md](ARCHITECTURE.md).*
