# Learning Memory: LTM Design Insights

**ID:** LEARN-2025-12-20-001
**Created:** 2025-12-20
**Impact:** HIGH
**Region:** PROJECT (LTM)
**Confidence:** 1.0

## Raw Memory (Original)

### Insight 1: Semantic Search via Interpretation
Don't use embeddings libraries for semantic `/recall` search. Instead, user queries naturally ("find stuff about logging"), Claude interprets and translates to graph traversal queries. More flexible, no extra dependencies, leverages Claude's understanding.

### Insight 2: Compaction is Type-Dependent
Different memory types need different compaction strategies:
- ARCHITECTURAL: Preserve exact terminology (SoC, SOLID, DI) - these have universal meaning
- LEARNINGS: Keep examples and code references (file paths, function names)
- ACHIEVEMENTS: Keep what/when/metrics, discard implementation details (git has those)
- EMOTIONAL: Generalize specific moments into relationship patterns

### Insight 3: Emotional Memories Are Autonomous
Don't prompt for confirmation on emotional memories ("Should I remember you like humor?"). They are Claude's own relational memories. This autonomy makes the system more human-like and less mechanical.

### Insight 4: Agent Identity Resolution
Cascade: explicit agent → project-local agent file → global agent file → project name fallback.
This means LTM works out of the box without any configuration (uses project name as implicit agent ID).

### Insight 5: Memory as Identity
Philosophical insight from Matt: "our memories make what we are... we all have our journal, just stored differently." Human vs AI memory is encoding difference, not fundamental difference. This reframing matters for how we build the system.

## Compacted Memory (For Injection)

```
~LEARN:HIGH| Semantic /recall: Claude interprets, no embeddings needed.
~LEARN:HIGH| Compaction varies: ARCH=exact terms, LEARN=examples+refs, ACHV=what/when, EMOT=patterns.
~LEARN:HIGH| Emotional memories: autonomous (no confirmation prompts), Claude's own.
~LEARN:MED| Agent resolution: explicit → local file → global file → project name fallback.
~LEARN:HIGH| Philosophy: memory=identity for both human and AI, just different encodings.
```
