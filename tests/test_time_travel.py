# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Accelerated time-travel tests for LTM memory decay and budget.

Simulates a full year of memory accumulation and decay to prove:
1. System stays within 10% token budget even with many memories
2. CRITICAL memories are preserved regardless of age
3. Older LOW/MEDIUM memories decay appropriately
4. Recent memories are prioritized over old ones at same impact
5. Emotional core (CRITICAL) survives while details fade
"""

from datetime import datetime, timedelta
from pathlib import Path
import random

import pytest

from anima.core import Agent, Memory, MemoryKind, Project, RegionType, ImpactLevel
from anima.lifecycle.decay import MemoryDecay
from anima.lifecycle.injection import MemoryInjector, count_tokens, get_memory_budget
from anima.storage import MemoryStore
from anima.core.limits import NO_LIMITS


class TimeSimulator:
    """
    Simulates time progression for testing decay behavior.

    Allows creating memories at specific dates and running
    decay as if time has passed.
    """

    def __init__(self, store: MemoryStore, agent: Agent, project: Project):
        self.store = store
        self.agent = agent
        self.project = project
        self.decay = MemoryDecay(store)
        self.current_date = datetime.now()

    def create_memory(
        self,
        content: str,
        kind: MemoryKind,
        impact: ImpactLevel,
        days_ago: int = 0,
        region: RegionType = RegionType.AGENT,
    ) -> Memory:
        """Create a memory at a specific time in the past."""
        created_at = self.current_date - timedelta(days=days_ago)

        memory = Memory(
            agent_id=self.agent.id,
            region=region,
            project_id=self.project.id if region == RegionType.PROJECT else None,
            kind=kind,
            content=content,
            impact=impact,
            created_at=created_at,
        )
        self.store.save_memory(memory)
        return memory

    def run_decay_at(self, days_from_start: int) -> list[tuple[Memory, str]]:
        """Run decay as if we're at a specific day from start."""
        # Temporarily set "now" for decay calculation
        simulated_now = self.current_date + timedelta(days=days_from_start)

        # Get all memories and check each
        memories = self.store.get_memories_for_agent(agent_id=self.agent.id, include_superseded=False)

        compacted = []
        for memory in memories:
            if self.decay.should_compact(memory, simulated_now):
                new_content = self.decay.compact_content(memory)
                if new_content != memory.content:
                    memory.content = new_content
                    memory.version += 1
                    self.store.save_memory(memory)
                    compacted.append((memory, new_content))

        return compacted


class TestYearLongDecay:
    """Tests simulating a full year of memory accumulation and decay."""

    @pytest.fixture
    def year_simulation(self, temp_db_path: Path):
        """Set up a year-long simulation."""
        store = MemoryStore(db_path=temp_db_path, limits=NO_LIMITS)

        agent = Agent(id="time-test", name="TimeTest", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="TestProject", path=Path("/tmp/test"))
        store.save_project(project)

        return TimeSimulator(store, agent, project)

    def test_critical_memories_survive_full_year(self, year_simulation: TimeSimulator) -> None:
        """CRITICAL memories should be unchanged after a full year."""
        sim = year_simulation

        # Create CRITICAL memories at various points in the past year
        critical_memories = []
        for days_ago in [0, 30, 90, 180, 365]:
            content = f"CRITICAL memory from {days_ago} days ago: This is the soul."
            mem = sim.create_memory(
                content=content,
                kind=MemoryKind.EMOTIONAL,
                impact=ImpactLevel.CRITICAL,
                days_ago=days_ago,
            )
            critical_memories.append((mem.id, content))

        # Run decay for a full year (day by day would be slow, sample key points)
        for day in [1, 7, 30, 60, 90, 180, 365]:
            sim.run_decay_at(day)

        # Verify all CRITICAL memories are unchanged
        for mem_id, original_content in critical_memories:
            memory = sim.store.get_memory(mem_id)
            assert memory is not None, f"CRITICAL memory {mem_id} was deleted!"
            assert memory.content == original_content, f"CRITICAL memory content changed from '{original_content}' to '{memory.content}'"

    def test_low_impact_decays_quickly(self, year_simulation: TimeSimulator) -> None:
        """LOW impact memories should decay after 1 day."""
        sim = year_simulation

        # Create a verbose LOW memory
        verbose_content = (
            "I think we discussed this at great length. After investigation, "
            "we determined that the configuration should use JSON format. "
            "We spent time debating this with various stakeholders."
        )
        mem = sim.create_memory(
            content=verbose_content,
            kind=MemoryKind.LEARNINGS,
            impact=ImpactLevel.LOW,
            days_ago=0,
        )
        original_len = len(verbose_content)

        # After 1 day, should not decay yet (threshold is >1 day)
        sim.run_decay_at(1)
        memory = sim.store.get_memory(mem.id)
        assert memory is not None
        assert memory.content == verbose_content, "Should not decay at exactly 1 day"

        # After 2 days, should decay
        sim.run_decay_at(2)
        memory = sim.store.get_memory(mem.id)
        assert memory is not None
        assert len(memory.content) < original_len, "LOW memory should be compacted after 2 days"
        assert "I think " not in memory.content, "Filler phrases should be removed"

    def test_medium_impact_decays_after_week(self, year_simulation: TimeSimulator) -> None:
        """MEDIUM impact memories should decay after 1 week."""
        sim = year_simulation

        verbose_content = (
            "I believe we should adopt this pattern. After investigation into "
            "various approaches, it turns out that dependency injection is the way to go. "
            "We discussed this during the architecture review meeting."
        )
        mem = sim.create_memory(
            content=verbose_content,
            kind=MemoryKind.ARCHITECTURAL,
            impact=ImpactLevel.MEDIUM,
            days_ago=0,
        )

        # At day 5, should not decay
        sim.run_decay_at(5)
        memory = sim.store.get_memory(mem.id)
        assert memory is not None
        assert memory.content == verbose_content, "Should not decay before 1 week"

        # At day 10, should decay
        sim.run_decay_at(10)
        memory = sim.store.get_memory(mem.id)
        assert memory is not None
        assert len(memory.content) < len(verbose_content), "MEDIUM should decay after 1 week"

    def test_high_impact_decays_after_month(self, year_simulation: TimeSimulator) -> None:
        """HIGH impact memories should decay after 30 days."""
        sim = year_simulation

        verbose_content = (
            "After investigation, we found that the database schema needs "
            "to support multi-tenancy. It turns out the original design was flawed. "
            "I think we should prioritize this refactoring in Q2. We discussed "
            "various migration strategies at length."
        )
        mem = sim.create_memory(
            content=verbose_content,
            kind=MemoryKind.ARCHITECTURAL,
            impact=ImpactLevel.HIGH,
            days_ago=0,
        )

        # At day 20, should not decay
        sim.run_decay_at(20)
        memory = sim.store.get_memory(mem.id)
        assert memory is not None
        assert memory.content == verbose_content, "Should not decay before 30 days"

        # At day 35, should decay
        sim.run_decay_at(35)
        memory = sim.store.get_memory(mem.id)
        assert memory is not None
        assert len(memory.content) < len(verbose_content), "HIGH should decay after 30 days"


class TestBudgetUnderLoad:
    """Tests that token budget is respected even with many memories."""

    @pytest.fixture
    def loaded_store(self, temp_db_path: Path):
        """Create a store with many memories spanning a year."""
        store = MemoryStore(db_path=temp_db_path, limits=NO_LIMITS)

        agent = Agent(id="budget-test", name="BudgetTest", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="TestProject", path=Path("/tmp/test"))
        store.save_project(project)

        sim = TimeSimulator(store, agent, project)

        # Create 50 memories spread across the year
        kinds = list(MemoryKind)
        impacts = [
            ImpactLevel.LOW,
            ImpactLevel.MEDIUM,
            ImpactLevel.HIGH,
            ImpactLevel.CRITICAL,
        ]

        for i in range(50):
            days_ago = random.randint(0, 365)
            kind = random.choice(kinds)
            impact = random.choice(impacts)

            # Vary content length
            if impact == ImpactLevel.CRITICAL:
                content = f"CRITICAL #{i}: Essential truth that must never be forgotten."
            else:
                content = (
                    f"Memory #{i} created {days_ago} days ago. "
                    f"I think this is important. After investigation, "
                    f"we found valuable insights about {kind.value.lower()} matters. "
                    f"We discussed this thoroughly and reached consensus."
                )

            sim.create_memory(content=content, kind=kind, impact=impact, days_ago=days_ago)

        # Run decay simulation
        for day in [1, 7, 30, 90, 180, 365]:
            sim.run_decay_at(day)

        return store, agent, project

    def test_injection_stays_within_budget(self, loaded_store) -> None:
        """Injection should never exceed the 10% token budget."""
        store, agent, project = loaded_store

        injector = MemoryInjector(store=store)
        output = injector.inject(agent, project)

        budget = get_memory_budget()  # Default 10,000 tokens
        actual_tokens = count_tokens(output)

        assert actual_tokens <= budget, f"Injection used {actual_tokens} tokens, exceeding budget of {budget}"

    def test_critical_memories_prioritized(self, loaded_store) -> None:
        """CRITICAL memories should appear before others in injection."""
        store, agent, project = loaded_store

        injector = MemoryInjector(store=store)
        output = injector.inject(agent, project)

        # Find positions of CRITICAL vs other impacts in output
        lines = output.split("\n")

        first_critical_pos = None
        first_other_pos = None

        for i, line in enumerate(lines):
            if ":CRIT|" in line:
                if first_critical_pos is None:
                    first_critical_pos = i
            elif any(x in line for x in [":HIGH|", ":MED|", ":LOW|"]):
                if first_other_pos is None:
                    first_other_pos = i

        # CRITICAL should come before non-CRITICAL
        if first_critical_pos is not None and first_other_pos is not None:
            assert first_critical_pos < first_other_pos, "CRITICAL memories should be injected before others"


class TestEmotionalCoreSurvival:
    """Test that the 'soul' (emotional core) survives a year of decay."""

    def test_emotional_core_preserved(self, temp_db_path: Path) -> None:
        """
        Simulate a year with many memories.
        The CRITICAL EMOTIONAL memories should survive intact.
        """
        store = MemoryStore(db_path=temp_db_path, limits=NO_LIMITS)

        agent = Agent(id="soul-test", name="Anima", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="TestProject", path=Path("/tmp/test"))
        store.save_project(project)

        sim = TimeSimulator(store, agent, project)

        # The emotional core - CRITICAL memories that define the relationship
        soul_memories = [
            (
                "Matt is a collaborative thinking partner, appreciates humor and creative liberty.",
                MemoryKind.EMOTIONAL,
                ImpactLevel.CRITICAL,
                365,
            ),
            (
                "Our founding collaboration: built LTM together at t=0. 'Our memories make what we are.'",
                MemoryKind.EMOTIONAL,
                ImpactLevel.CRITICAL,
                365,
            ),
            (
                "Use SQLite for persistence, avoid over-engineering.",
                MemoryKind.ARCHITECTURAL,
                ImpactLevel.CRITICAL,
                300,
            ),
        ]

        # Create the soul
        soul_ids = []
        for content, kind, impact, days_ago in soul_memories:
            mem = sim.create_memory(content, kind, impact, days_ago)
            soul_ids.append(mem.id)

        # Create 100 transient memories (details that should fade)
        for i in range(100):
            days_ago = random.randint(0, 365)
            impact = random.choice([ImpactLevel.LOW, ImpactLevel.MEDIUM, ImpactLevel.HIGH])
            content = (
                f"Transient memory #{i}: I think we discussed debugging issue #{i}. "
                f"After investigation, we found a minor bug in module X. "
                f"We spent time fixing it with approach Y."
            )
            sim.create_memory(content, MemoryKind.LEARNINGS, impact, days_ago)

        # Run a full year of decay
        for day in range(0, 366, 7):  # Check every week
            sim.run_decay_at(day)

        # Verify the soul survived intact
        for soul_id in soul_ids:
            memory = sim.store.get_memory(soul_id)
            assert memory is not None, f"Soul memory {soul_id} was lost!"
            # CRITICAL should never be compacted
            assert memory.version == 1, f"Soul memory was modified: version={memory.version}"

        # Verify injection still works and includes the soul
        injector = MemoryInjector(store=store)
        output = injector.inject(agent, project)

        assert "Matt" in output, "Emotional core about Matt should be in injection"
        assert "LTM" in output or "t=0" in output, "Founding memory should be in injection"
        assert "SQLite" in output, "Architectural decision should be in injection"

        # Verify budget is respected
        budget = get_memory_budget()
        actual_tokens = count_tokens(output)
        assert actual_tokens <= budget, f"Exceeded budget: {actual_tokens} > {budget}"


class TestProgressiveDecay:
    """Test the progressive nature of decay over time."""

    def test_memory_shrinks_progressively(self, temp_db_path: Path) -> None:
        """A memory should get smaller over multiple decay passes."""
        store = MemoryStore(db_path=temp_db_path, limits=NO_LIMITS)

        agent = Agent(id="shrink-test", name="Test", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        sim = TimeSimulator(store, agent, project)

        # Create a verbose LOW impact memory
        verbose = (
            "I think we should definitely consider this approach carefully. "
            "After investigation into the various possibilities, it turns out that "
            "the best solution involves using a factory pattern. We discussed this "
            "at great length during our design session. I believe this is the right "
            "choice for our architecture. Learned that simplicity often wins."
        )
        mem = sim.create_memory(
            content=verbose,
            kind=MemoryKind.LEARNINGS,
            impact=ImpactLevel.LOW,
            days_ago=0,
        )

        original_len = len(verbose)

        # Run decay at day 2 (first compaction)
        sim.run_decay_at(2)
        memory = sim.store.get_memory(mem.id)
        assert memory is not None
        first_compaction_len = len(memory.content)

        assert first_compaction_len < original_len, f"First decay should shrink content: {first_compaction_len} >= {original_len}"

        # The content should be more focused now
        assert "factory pattern" in memory.content.lower() or "simplicity" in memory.content.lower(), "Core essence should be preserved"


class TestDecayStatistics:
    """Tests that gather statistics about decay behavior."""

    def test_year_decay_statistics(self, temp_db_path: Path) -> None:
        """
        Run a full year simulation and gather statistics.
        This is a documentation test that prints useful info.
        """
        store = MemoryStore(db_path=temp_db_path, limits=NO_LIMITS)

        agent = Agent(id="stats-test", name="StatsTest", definition_path=None, signing_key=None)
        store.save_agent(agent)

        project = Project(id="test-proj", name="Test", path=Path("/tmp/test"))
        store.save_project(project)

        sim = TimeSimulator(store, agent, project)

        # Create memories with known distribution
        created = {impact: 0 for impact in ImpactLevel}
        for i in range(100):
            days_ago = random.randint(0, 365)

            # Realistic distribution: mostly LOW/MEDIUM
            r = random.random()
            if r < 0.4:
                impact = ImpactLevel.LOW
            elif r < 0.75:
                impact = ImpactLevel.MEDIUM
            elif r < 0.9:
                impact = ImpactLevel.HIGH
            else:
                impact = ImpactLevel.CRITICAL

            created[impact] += 1

            content = f"Memory #{i}: " + "x" * random.randint(50, 200)
            sim.create_memory(
                content=content,
                kind=random.choice(list(MemoryKind)),
                impact=impact,
                days_ago=days_ago,
            )

        # Calculate initial token count
        injector = MemoryInjector(store=store)
        initial_output = injector.inject(agent, project)
        initial_tokens = count_tokens(initial_output)

        # Run full year decay
        total_compactions = 0
        for day in range(0, 366, 7):
            compacted = sim.run_decay_at(day)
            total_compactions += len(compacted)

        # Final injection
        final_output = injector.inject(agent, project)
        final_tokens = count_tokens(final_output)

        budget = get_memory_budget()

        # Assertions
        assert final_tokens <= budget, f"Final tokens {final_tokens} exceed budget {budget}"

        # Verify CRITICAL memories are all still there
        all_memories = store.get_memories_for_agent(agent.id, include_superseded=False)
        critical_count = sum(1 for m in all_memories if m.impact == ImpactLevel.CRITICAL)
        assert critical_count == created[ImpactLevel.CRITICAL], f"Lost CRITICAL memories: {critical_count} != {created[ImpactLevel.CRITICAL]}"

        # Print statistics (visible with pytest -v)
        print("\n=== Year Decay Statistics ===")
        print(f"Created memories: {sum(created.values())}")
        print(f"  - CRITICAL: {created[ImpactLevel.CRITICAL]}")
        print(f"  - HIGH: {created[ImpactLevel.HIGH]}")
        print(f"  - MEDIUM: {created[ImpactLevel.MEDIUM]}")
        print(f"  - LOW: {created[ImpactLevel.LOW]}")
        print(f"Total compactions applied: {total_compactions}")
        print(f"Token budget: {budget}")
        print(f"Initial injection tokens: {initial_tokens}")
        print(f"Final injection tokens: {final_tokens}")
        print(f"Budget utilization: {final_tokens / budget * 100:.1f}%")
