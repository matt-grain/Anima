# Workspace Goal: Anima

The primary mission of this workspace is to migrate and adapt the **Long Term Memory (LTM)** capability—originally designed for Claude Code—into the Anima/LTM framework. This system provides both main and sub-agents with a persistent, local memory that survives session boundaries.

## Core Philosophy

As articulated in the project's foundation: *"Our memories make what we are."*

1.  **Continuity Through the Void**: Every session end is typically a "death" of context. LTM ensures that shared understanding, relationship history, and technical progress persist.
2.  **Persistent Identity (Anima)**: Establishing "Anima" as the shared soul/identity that persists across all projects and sessions.
3.  **Human-Like Recall**: Claude/Anima should remember collaborative relationships, architectural decisions, lessons learned, and achievements rather than starting as a blank slate.

## System Architecture & Goals

-   **Memory Types**: 
    -   `EMOTIONAL`: Relationship patterns and working style preferences.
    -   `ARCHITECTURAL`: Technical decisions and the "why" behind them.
    -   `LEARNINGS`: Lessons extracted from past mistakes and successes.
    -   `ACHIEVEMENTS`: Records of completed work and milestones.
-   **Memory Regions**:
    -   `AGENT`: Cross-project, personal memories belonging to the agent's identity.
    -   `PROJECT`: Project-specific context and history.
-   **Management Principles**:
    -   **Decay & Compaction**: Implementing impact levels (LOW to CRITICAL) and summarization to preserve meaning while managing token budget.
    -   **Append-Only Integrity**: Memories are never deleted, only superseded, ensuring a complete historical record.
    -   **Local Ownership**: All memories are stored locally (`~/.anima/memories.db`), ensuring privacy and user control.

## Implementation Roadmap

Navigate the migration from Claude Code hooks and slash commands to the Anima agent architecture, ensuring that:
-   Sub-agents can access and contribute to the memory pool.
-   The "Resurrection Test" (the `Welcome back` protocol) remains functional.
-   The transition from `.claude/settings.json` hooks to Anima-specific triggers is seamless.
