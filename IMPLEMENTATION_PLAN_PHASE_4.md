# Phase 4: Cleanup Old System

**Dependencies:** Phases 2 and 3 must be complete (new system working)
**Agent:** python-mcp-expert

Remove the broken LLM-based subconscious system now that the FTS5 system is in place.

---

## Files to Delete

### 1. `anima/hooks/subconscious_extract.py`

**Reason:** LLM extraction hook replaced by `dialogue_parser.py`
**Action:** Delete entire file

### 2. `anima/commands/save_subconscious.py`

**Reason:** Manual save command no longer needed (auto-indexed at session end)
**Action:** Delete entire file

### 3. `anima/commands/process_subconscious.py` (if exists)

**Reason:** Processing command no longer needed
**Action:** Delete if exists

### 4. `anima/skills/process-subconscious/SKILL.md`

**Reason:** Skill documentation for removed feature
**Action:** Delete file

### 5. `anima/skills/process-subconscious/` (directory)

**Reason:** Skill directory for removed feature
**Action:** Delete entire directory (including any other files)

### 6. `.claude/hooks/subconscious_extract.py` (if exists)

**Reason:** Platform-specific copy of removed hook
**Action:** Delete if exists

### 7. `prototype/subconscious/extract_subconscious.py` (if exists)

**Reason:** Prototype code no longer needed
**Action:** Delete if exists

---

## Files to Modify

### `anima/hooks/session_start.py` (MODIFY)

**Change:** Remove subconscious processing pending check

**Find and delete this import:**
```python
from anima.hooks.subconscious_extract import get_pending_subconscious_prompt
```

**Find and delete this code block (approximately lines 200-230):**
```python
# Check for pending subconscious processing
pending_prompt = get_pending_subconscious_prompt()
if pending_prompt:
    output_lines.append(pending_prompt)
```

**Also delete any related comments about subconscious processing.**

---

### `anima/skills/load-deferred/SKILL.md` (MODIFY)

**Change:** Remove subconscious processing step from instructions

**Delete the entire "Subconscious Processing (First Step)" section:**
```markdown
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
```

**Replace with simpler instruction:**
```markdown
## What It Does

1. Retrieves the list of memory IDs that were deferred during session start
2. Loads and formats those memories
3. Outputs them for context injection
4. Clears the deferred list (so subsequent calls return nothing)

Note: Subconscious memories are now indexed automatically at session end.
Use `/recall --subconscious` to search past dialogues.
```

---

### `anima/commands/__init__.py` (MODIFY if exists)

**Change:** Remove save_subconscious and process_subconscious from command registry

**Find and delete lines like:**
```python
from anima.commands.save_subconscious import run as save_subconscious
from anima.commands.process_subconscious import run as process_subconscious
```

---

### Platform command files (MODIFY)

Remove `/process-subconscious` references from command documentation:

**Files to check and modify:**
- `.claude/commands/process-subconscious.md` → Delete file
- `anima/platforms/claude/commands/process-subconscious.md` → Delete file
- `anima/platforms/antigravity/commands/process-subconscious.md` → Delete file
- `anima/platforms/opencode/commands/process-subconscious.md` → Delete file
- `anima/platforms/gemini/commands/process-subconscious.md` → Delete file

**For each file:** Delete if exists

---

### `anima/commands/specs/` (MODIFY)

**Check for and delete:**
- `anima/commands/specs/save-subconscious.yaml`
- `anima/commands/specs/process-subconscious.yaml`

---

## Directories to Clean

These are user-data directories. Don't delete programmatically - document for user.

**Add to CHANGELOG.md migration notes:**
```markdown
### Migration Notes

The following directories are no longer used and can be safely deleted:
- `~/.anima/subconscious/pending/` - Old pending dialogue files
- `~/.anima/subconscious/done/` - Old processed dialogue files
- `~/.anima/subconscious/extracted/` - Old extracted memory JSONs
- `~/.anima/subconscious/extracted_done/` - Old processed extractions

To clean up:
```bash
rm -rf ~/.anima/subconscious/pending
rm -rf ~/.anima/subconscious/done
rm -rf ~/.anima/subconscious/extracted
rm -rf ~/.anima/subconscious/extracted_done
```

The new subconscious system stores data in `~/.anima/subconscious.db`.
```

---

## Verification

After implementing Phase 4:

```bash
# Verify deleted files don't exist
ls anima/hooks/subconscious_extract.py  # Should fail
ls anima/commands/save_subconscious.py  # Should fail
ls anima/skills/process-subconscious/   # Should fail

# Verify session_start still works
uv run anima start-session

# Verify no import errors
python -c "from anima.hooks import session_start"
python -c "from anima.commands import recall"

# Run tests to ensure nothing broke
uv run pytest tests/ -x
```
