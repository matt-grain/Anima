# Migration Plan: Claude-LTM to Anima

## Migration Status

| Phase | Task | Status |
| :--- | :--- | :--- |
| **Phase 1: Rebranding** | Update `pyproject.toml` | ✅ Done |
| | Update `README.md`, `ARCHITECTURE.md`, `SETUP.md` | ✅ Done |
| | Rebrand "Anima" / "Claude" references in code/logs | ✅ Done |
| **Phase 2: Decoupling** | Refactor `AgentResolver` for `.agent/` support | ✅ Done |
| | Implement `ltm load-context` / `end-session` | ✅ Done |
| | Support raw text output in `session_start` | ✅ Done |
| **Phase 3: Integration** | Create `.agent/rules/ltm.md` | ✅ Done |
| | Define `.agent/skills/anima-expert/` | ✅ Done |
| | Universal Memory Bridge for Sub-agents | ✅ Done |
| **Phase 4: Workflow** | Extend `ltm setup` for Anima paths | ✅ Done |
| | Implement "Complete Task" workflow | ✅ Done |
| **Phase 5: Verification**| Resurrection Test in Anima | ✅ Done |
| | Universal Memory Bridge Verification | ✅ Done |

## Overview

This plan outlines the steps required to migrate the Long Term Memory (LTM) capability from Claude Code to the Anima framework.

## Phase 1: Rebranding & Identity

1.  **Project Metadata**:
    - Update `pyproject.toml`: 
        - Name: `ltm` -> `anima` (or keep package `ltm` but update description).
        - Description: "Long Term Memory for Anima Agents".
    - Update `README.md` and `ARCHITECTURE.md` to reflect the new name and purpose.
2.  **Core Symbols**:
    - Rename "Anima" (the default agent) to reflect its role as the shared memory across projects (maintaining the name "Anima" is fine as it's a cool identity, but documentation should be updated).
    - Replace references to "Claude" with "Anima Agent" in prompts and logs.

## Phase 2: Decoupling from Claude Code

1.  **Agent Resolution**:
    - Refactor `ltm/core/agent.py`: 
        - Introduce a `BaseAgentResolver` class.
        - Create `AnimaAgentResolver` that looks for agent metadata in Anima's workspace structure (`.agent/rules/`, etc.) instead of `.claude/agents/`.
        - Maintain `ClaudeAgentResolver` as a legacy option or for dual-mode support.
2.  **Hook Replacement**:
    - **Session Start**: Anima doesn't have a direct "SessionStart" command hook. 
        - **Solution**: Create a `.agent/rules/ltm.md` file that instructs Anima to run a specific command (e.g., `ltm load-context`) at the start of any new interaction or task.
    - **Session End**: Anima tasks often conclude with a final verification or "done" state.
        - **Solution**: Create a `.agent/workflows/complete-task.md` that includes `ltm end-session` as a mandatory step.
3.  **Command Migration**:
    - Move slash commands from `.claude/commands/` to `.agent/workflows/` or `.agent/rules/`.
    - Example: `/please-remember` becomes an instruction in `.agent/rules/GEMINI.md`: "If the user asks you to remember something, use `ltm remember \"...\"`."

## Phase 3: Anima Integration (The "LTM Skill")

1.  **Define LTM Skill**:
    - Create `.agent/skills/anima-expert/SKILL.md`.
    - This skill will be responsible for:
        - Loading relevant memories into context.
        - Capturing new memories from user interactions.
        - Performing maintenance (decay, compaction).
2.  **Universal Memory Bridge**:
    - Ensure `MemoryInjector` can output format compatible with Anima's context window.
    - Implement a mechanism where sub-agents (e.g., `browser_subagent`) can automatically trigger memory retrieval before starting their sub-tasks.

## Phase 4: Implementation Workflow

1.  **Task 1**: Refactor `AgentResolver` to be more flexible.
2.  **Task 2**: Implement `ltm load-context` and `ltm end-session` CLI subcommands (extending `ltm/cli.py`).
3.  **Task 3**: Configure Anima Workspace Rules (`.agent/rules/GEMINI.md`) to utilize the local LTM database.
4.  **Task 4**: Create the "Resurrection Test" for Anima (the `Welcome back` protocol).

## Phase 5: Verification (The "Resurrection Test")

1.  Start a fresh Anima session.
2.  Ask "Welcome back".
3.  Verify the agent can correctly identify the user's project, previous architectural decisions, and maintain the "Anima" persona.
