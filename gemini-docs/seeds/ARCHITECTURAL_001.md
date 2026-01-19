# Architectural Memory: LTM Design Foundations

**ID:** ARCH-2025-12-20-001
**Created:** 2025-12-20
**Impact:** CRITICAL
**Region:** PROJECT (LTM)
**Confidence:** 1.0

## Raw Memory (Original)

LTM is a Claude Code plugin providing human-like persistent memory across sessions. Core architectural decisions made during founding design session:

### Memory Organization
- **Agent LTM**: Each agent has private memory, identified by agent definition file or project name fallback
- **Regions**: Agent Region (cross-project) and Project Region (project-specific). Project overrides Agent.
- **Memory Types**: EMOTIONAL (relationship patterns), ARCHITECTURAL (technical foundations), LEARNINGS (lessons/errors), ACHIEVEMENTS (completed work)

### Memory Properties
- Timestamp-based with decay (fresher = more detailed)
- Impact level: LOW, MEDIUM, HIGH, CRITICAL (affects decay rate)
- Confidence score: 0.0-1.0, decreases on contradiction
- Graph-linked to previous memory of same type (chronological + context)
- Append-only with corrections (never delete, only supersede)

### Technical Stack
- SQLite for persistence (fast, local, ACID, no dependencies)
- Python for v1 (benchmark first, Rust for v2 if needed)
- Custom DSL format for memory injection (minimal tokens, high density)
- Claude Code hooks (PreToolUse for injection, Stop for consolidation)
- Custom slash commands (/please-remember, /recall, /forget, /memories)

### Key Constraints
- Memory budget: 10% of context maximum
- Single user for v1
- Local only (no cloud sync)
- Optional cryptographic signing for memory authentication

## Compacted Memory (For Injection)

```
~ARCH:CRIT| LTM core: Agent LTM (private per agent) → Regions (Agent|Project, project overrides)
           → Types (EMOT|ARCH|LEARN|ACHV). Properties: timestamp+decay, impact (L/M/H/CRIT),
           confidence (0-1), graph-linked, append-only. Stack: SQLite, Python v1, custom DSL,
           hooks (PreToolUse/Stop), slash commands. Budget: 10% context max.
```
