---
name: auto-memory
description: Automatically remember and recall important events without user prompting
license: MIT
compatibility: opencode
metadata:
  audience: agents
  workflow: continuous
---

## What I do

Automatically capture and retrieve memories for significant project events and interactions:

### Auto-Remember Events

Proactively use `uv run anima remember <parameters> "text"` when:

**Feature completion**
- Finishing a multi-step feature implementation
- Completing a bug fix or refactoring
- Successful test suite results
- Deploying or releasing code

**Git milestones**
- After significant commits (feature completion, major fixes)
- Merging pull requests
- Tagging releases

**User interactions**
- Learning user preferences, goals, or context
- Discovering important project details
- Having valuable technical discussions
- User explicitly sharing information (names, preferences, etc.)

**System events**
- Successfully resolving complex issues
- Learning new codebase patterns
- Understanding project architecture

Memory format: `--impact <IMPACT> --kind <KIND> --region <REGION> --project <PROJECT if region is PROJECT> "<concise description>"`

**Memory kinds:**
- `EMOTIONAL`: User preferences, personal context, emotional states, relationships
- `ARCHITECTURAL`: Project structure, design patterns, technical decisions, codebase insights
- `LEARNINGS`: Problem solutions, debugging insights, new discoveries, best practices
- `ACHIEVEMENTS`: Completed features, milestones, successful deployments, major fixes

**Memory regions:**
- `AGENT`: Agent-specific memories, personal context, agent's own learnings (default)
- `PROJECT`: Project-specific memories, architectural details, team decisions (requires `--project <PATH>`)

### Auto-Recall Events

Proactively use `uv run anima recall <parameters>` when:

- Starting a new session
- Encountering similar problems to past solutions
- User context seems relevant to stored memories
- Before starting significant work on the project
- After recalling successful patterns from past work

**Timing context**
- On session.start events
- When user mentions "welcome back" or similar greetings
- Before implementing features related to past work

## When to use me

Use this skill continuously throughout development. No explicit activation needed - this describes automatic behavior for memory management.

## Memory importance guidelines

- **High**: Successful feature completion, critical bug fixes, major achievements, user preferences, important architectural insights
- **Medium**: Test improvements, refactoring, helpful discussions, minor fixes
- **Low**: Small code adjustments, routine maintenance, minor optimizations
