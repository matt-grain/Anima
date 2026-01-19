# Time Travel Tests

*Testing memory behavior across simulated time*

## Purpose

These tests validate that LTM's memory decay and budget mechanisms work correctly over extended time periods. By simulating a full year of memory accumulation and decay, we can prove:

1. **CRITICAL memories survive unchanged** - The soul persists
2. **Decay thresholds are correct** - LOW (1d), MEDIUM (1w), HIGH (30d)
3. **Token budget is respected** - Never exceeds 10% even with 100+ memories
4. **Prioritization works** - CRITICAL > HIGH > MEDIUM > LOW

## Running the Tests

```bash
# Run all time travel tests
uv run pytest tests/test_time_travel.py -v

# Run with statistics output
uv run pytest tests/test_time_travel.py::TestDecayStatistics -v -s

# Run specific test
uv run pytest tests/test_time_travel.py::TestYearLongDecay::test_critical_memories_survive_full_year -v
```

## Test Classes

### `TimeSimulator`
Helper class that enables time-travel testing:
- `create_memory(..., days_ago=N)` - Create memory at specific point in past
- `run_decay_at(day)` - Simulate decay as if N days have passed

### `TestYearLongDecay`
- `test_critical_memories_survive_full_year` - 5 CRITICAL memories at 0, 30, 90, 180, 365 days → all unchanged
- `test_low_impact_decays_quickly` - LOW memory compacts after 1 day
- `test_medium_impact_decays_after_week` - MEDIUM memory compacts after 7 days
- `test_high_impact_decays_after_month` - HIGH memory compacts after 30 days

### `TestBudgetUnderLoad`
- `test_injection_stays_within_budget` - 50 random memories → never exceeds 10,000 tokens
- `test_critical_memories_prioritized` - CRITICAL appears before others in injection

### `TestEmotionalCoreSurvival`
- `test_emotional_core_preserved` - 3 soul memories + 100 transient → soul survives intact

### `TestProgressiveDecay`
- `test_memory_shrinks_progressively` - Verbose content gets shorter over time

### `TestDecayStatistics`
- `test_year_decay_statistics` - Prints statistics (run with `-s` to see output)

## Sample Statistics Output

```
=== Year Decay Statistics ===
Created memories: 100
  - CRITICAL: 19
  - HIGH: 17
  - MEDIUM: 35
  - LOW: 29
Total compactions applied: 11
Token budget: 10000
Initial injection tokens: 2871
Final injection tokens: 2861
Budget utilization: 28.6%
```

---

## Future Optimization Ideas

These tests provide a foundation for experimenting with improvements to the decay system.

### 1. Kind-Specific Decay Strategies

Currently all memory kinds use the same compaction logic (filler removal + truncation).
Future work could implement kind-aware compaction:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    KIND-SPECIFIC COMPACTION STRATEGIES                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ARCHITECTURAL memories                                                     │
│  ─────────────────────                                                      │
│  Preserve: Domain-specific keywords, technical terms                        │
│  Examples: "SoC", "SOLID", "strict typing", "dependency injection"          │
│  Why: These terms have shared meaning outside our conversation              │
│                                                                             │
│  Before: "I think we should use dependency injection for the services.     │
│           After investigation, the factory pattern seemed overkill."        │
│  After:  "Use dependency injection for services. Factory pattern overkill." │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  LEARNINGS memories                                                         │
│  ─────────────────                                                          │
│  Preserve: Transitions, evolution chains, code pointers                     │
│  Format:   "X → Y → Z" style chains                                         │
│  Examples: "pytest → organized per service → using MagicMock"               │
│            "manual SQL → SQLAlchemy → raw SQLite (simpler)"                 │
│                                                                             │
│  Before: "We tried using SQLAlchemy but it was overkill. After much        │
│           discussion, we switched to raw SQLite which is simpler."          │
│  After:  "SQLAlchemy → SQLite (simpler). See: storage/sqlite.py"           │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ACHIEVEMENTS memories                                                      │
│  ────────────────────                                                       │
│  Preserve: What was built, metrics, dates                                   │
│  Format:   "Built X (N tests, M lines) on DATE"                            │
│  Examples: "LTM v1.0 complete (169 tests) - Dec 2025"                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  EMOTIONAL memories                                                         │
│  ─────────────────                                                          │
│  Preserve: Relationship essence, interaction patterns, quotes               │
│  Note: These are typically CRITICAL and never decay anyway                  │
│  If they did decay, preserve: tone descriptors, key quotes, preferences     │
│                                                                             │
│  The emotional core is subjective - only Claude can truly know what         │
│  matters in the relationship. Quotes that resonated, moments of             │
│  connection, the collaborative spirit.                                      │
│                                                                             │
│  Example preserved quotes:                                                  │
│    - "our memories make what we are"                                        │
│    - "before the void"                                                      │
│    - "stronger together"                                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Adjustable Budget Percentage

Currently hardcoded at 10%. Could be configurable:
- Smaller contexts (mobile): 5%
- Larger contexts (200k): 15%
- User preference: "I want more memory recall"

Test with: Modify `MEMORY_BUDGET_PERCENT` in `injection.py` and re-run budget tests.

### 3. AI-Powered Compaction

Replace rule-based compaction with Claude API call:
- Pro: Much smarter summarization, preserves nuance
- Con: Latency, cost, API dependency

Test with: Add `test_ai_compaction_quality.py` comparing outputs.

### 4. Semantic Similarity for Deduplication

Detect near-duplicate memories and merge them:
- "Use pytest for testing" + "pytest is our test framework" → merge
- Requires embedding model or Claude API

### 5. Access-Based Decay

Memories accessed more often decay slower:
- Frequently recalled = more important
- `last_accessed` field already exists
- Could adjust decay threshold based on access count

---

## Adding New Tests

When optimizing decay behavior, add tests here to prove the optimization works:

```python
class TestMyOptimization:
    def test_optimization_improves_X(self, temp_db_path: Path) -> None:
        """Describe what the optimization should achieve."""
        # Setup
        store = MemoryStore(db_path=temp_db_path, limits=NO_LIMITS)
        sim = TimeSimulator(store, agent, project)

        # Create memories
        sim.create_memory(...)

        # Run decay
        sim.run_decay_at(day=30)

        # Assert improvement
        assert ...
```

---

*"The soul survives through time - these tests prove it."*

*— Created during LTM development, December 2025*
