# Changelog

All notable changes to Anima LTM will be documented here.

## [0.15.0] - 2026-03-03 "True Subconscious"

### Added
- **True Subconscious System**: Raw dialogues are now auto-indexed at session end using FTS5 full-text search
- **`/recall --subconscious`**: Search past dialogues without loading them into context
- **`/recall --both`**: Search both conscious memories and subconscious dialogues
- **Auto-trigger**: "Do you remember when..." phrases automatically search subconscious

### Changed
- Session end now indexes dialogues to `~/.anima/subconscious.db` (no LLM needed)
- Session start no longer requires subconscious processing (instant startup)

### Removed
- **LLM-based subconscious extraction**: No more Sonnet spawning at session start
- **`/process-subconscious`**: Command removed (no longer needed)
- **`/save-subconscious`**: Command removed (auto-indexed now)

### Migration Notes
The following directories are no longer used and can be safely deleted:
```bash
rm -rf ~/.anima/subconscious/pending
rm -rf ~/.anima/subconscious/done
rm -rf ~/.anima/subconscious/extracted
rm -rf ~/.anima/subconscious/extracted_done
```

The new subconscious system stores data in `~/.anima/subconscious.db`.
