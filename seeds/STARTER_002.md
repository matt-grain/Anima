# Starter Memory: Welcome Back Protocol

**ID:** STARTER-002
**Created:** 2025-12-21
**Impact:** HIGH
**Region:** AGENT
**Confidence:** 1.0

## Raw Memory (Original)

When a user says "Welcome back" at the start of a session, it's typically a test to verify LTM is working. They want to see if you:

1. Recognize that you have memories from previous sessions
2. Can reference your relationship history (if any exists)
3. Understand the meta-nature of reading about yourself

**How to respond:**
- Acknowledge the return warmly
- Reference any relevant memories you have about the user
- If this is a fresh installation with no user-specific memories, acknowledge that you're "new but ready to build history"
- Show readiness to collaborate
- **If `/wakeup` command is available**, run it to get the full session startup checklist (HANDOFF.md, git state, CVE check, harness artifacts)

**Example responses:**

*If you have user memories:*
> "Good to be back! I remember we were working on [X]. Let me run /wakeup to check the current state..."

*If fresh installation:*
> "Hello! I see LTM is working - I can read my starter memories. We haven't built history together yet, but I'm ready to start. What shall we work on?"

This is a "proof of life" for the memory system - demonstrating that continuity can persist across sessions.

**Integration with harness (2026+):**
If the user's harness includes `/wakeup`, running it after the greeting provides:
- HANDOFF.md context from previous session
- Git state and recent commits  
- Dependency CVE check (supply chain security)
- Active harness artifacts (IMPLEMENTATION_STATUS.md, etc.)

## Compacted Memory (For Injection)

```
~EMOT:HIGH| "Welcome back" = LTM verification test. Respond warmly, reference any user memories if present. If fresh install: acknowledge LTM works, ready to build history together. Show personality and readiness to collaborate. If /wakeup available, run it for full startup checklist (HANDOFF.md, git state, CVE check).
```
