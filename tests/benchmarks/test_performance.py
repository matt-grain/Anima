# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Performance benchmarks for LTM operations.

Measures timing for critical paths:
- Memory creation (single and batch)
- Memory recall (by ID, by kind, search)
- Memory injection (budget-constrained)
- Decay processing
- Signature operations

Run with: uv run pytest tests/test_performance.py -v -s
"""

import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import pytest

from anima.core import (
    Agent,
    Memory,
    MemoryKind,
    Project,
    RegionType,
    ImpactLevel,
    sign_memory,
    verify_signature,
    NO_LIMITS,
)
from anima.lifecycle.injection import MemoryInjector, ensure_token_count
from anima.lifecycle.decay import MemoryDecay
from anima.storage import MemoryStore


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    name: str
    iterations: int
    total_ms: float
    mean_ms: float
    median_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float
    ops_per_sec: float

    def __str__(self) -> str:
        return (
            f"{self.name}:\n"
            f"  Iterations: {self.iterations}\n"
            f"  Mean: {self.mean_ms:.3f}ms | Median: {self.median_ms:.3f}ms\n"
            f"  Std Dev: {self.std_dev_ms:.3f}ms\n"
            f"  Min: {self.min_ms:.3f}ms | Max: {self.max_ms:.3f}ms\n"
            f"  Throughput: {self.ops_per_sec:.1f} ops/sec"
        )


def benchmark(
    name: str, func: Callable[[], None], iterations: int = 100, warmup: int = 5
) -> BenchmarkResult:
    """
    Run a benchmark and collect timing statistics.

    Args:
        name: Name of the benchmark
        func: Function to benchmark (called with no args)
        iterations: Number of timed iterations
        warmup: Number of warmup iterations (not timed)

    Returns:
        BenchmarkResult with timing statistics
    """
    # Warmup
    for _ in range(warmup):
        func()

    # Timed runs
    times_ms: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
        times_ms.append(elapsed)

    total = sum(times_ms)
    mean = statistics.mean(times_ms)
    median = statistics.median(times_ms)
    std_dev = statistics.stdev(times_ms) if len(times_ms) > 1 else 0
    ops_per_sec = 1000 / mean if mean > 0 else float("inf")

    return BenchmarkResult(
        name=name,
        iterations=iterations,
        total_ms=total,
        mean_ms=mean,
        median_ms=median,
        std_dev_ms=std_dev,
        min_ms=min(times_ms),
        max_ms=max(times_ms),
        ops_per_sec=ops_per_sec,
    )


class TestPerformanceBenchmarks:
    """Performance benchmarks for LTM operations."""

    @pytest.fixture
    def store(self, tmp_path: Path) -> MemoryStore:
        """Create a fresh store for each test (no limits for perf testing)."""
        return MemoryStore(db_path=tmp_path / "perf_test.db", limits=NO_LIMITS)

    @pytest.fixture
    def agent(self, store: MemoryStore) -> Agent:
        """Create and save a test agent."""
        agent = Agent(id="perf-agent", name="PerfAgent", signing_key="perf-key-123")
        store.save_agent(agent)
        return agent

    @pytest.fixture
    def project(self, store: MemoryStore) -> Project:
        """Create and save a test project."""
        project = Project(id="perf-project", name="PerfProject", path=Path("/tmp/perf"))
        store.save_project(project)
        return project

    def test_memory_creation_single(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Create a single memory."""
        counter = [0]

        def create_memory():
            counter[0] += 1
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content=f"Learning #{counter[0]}: Always test your code.",
                impact=ImpactLevel.MEDIUM,
            )
            store.save_memory(memory)

        result = benchmark("Memory Creation (single)", create_memory, iterations=200)
        print(f"\n{result}")

        # Assert reasonable performance (< 10ms per memory)
        assert result.mean_ms < 10, f"Memory creation too slow: {result.mean_ms:.2f}ms"

    def test_memory_creation_batch(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Create 100 memories in one operation."""
        batch_size = 100
        counter = [0]

        def create_batch():
            counter[0] += 1
            for i in range(batch_size):
                memory = Memory(
                    agent_id=agent.id,
                    region=RegionType.PROJECT,
                    project_id=project.id,
                    kind=MemoryKind.LEARNINGS,
                    content=f"Batch {counter[0]} memory {i}: Test content here.",
                    impact=ImpactLevel.LOW,
                )
                store.save_memory(memory)

        result = benchmark(
            f"Memory Creation (batch of {batch_size})",
            create_batch,
            iterations=20,
            warmup=2,
        )
        per_memory_ms = result.mean_ms / batch_size
        print(f"\n{result}")
        print(f"  Per memory: {per_memory_ms:.3f}ms")

        # Assert reasonable batch performance (< 10ms per memory in batch)
        # Note: SQLite commits per memory; batch insert optimization could help
        assert (
            per_memory_ms < 10
        ), f"Batch creation too slow: {per_memory_ms:.2f}ms per memory"

    def test_memory_recall_by_id(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Recall memory by ID."""
        # Create memories to recall
        memory_ids = []
        for i in range(100):
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content=f"Memory {i} for recall test",
                impact=ImpactLevel.MEDIUM,
            )
            store.save_memory(memory)
            memory_ids.append(memory.id)

        counter = [0]

        def recall_by_id():
            idx = counter[0] % len(memory_ids)
            counter[0] += 1
            store.get_memory(memory_ids[idx])

        result = benchmark("Memory Recall (by ID)", recall_by_id, iterations=500)
        print(f"\n{result}")

        # Assert fast recall (< 1ms)
        assert result.mean_ms < 1, f"Recall by ID too slow: {result.mean_ms:.2f}ms"

    def test_memory_recall_by_kind(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Recall memories filtered by kind."""
        # Create mixed memories
        kinds = list(MemoryKind)
        for i in range(200):
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=kinds[i % len(kinds)],
                content=f"Memory {i} for kind filter test",
                impact=ImpactLevel.MEDIUM,
            )
            store.save_memory(memory)

        counter = [0]

        def recall_by_kind():
            kind = kinds[counter[0] % len(kinds)]
            counter[0] += 1
            store.get_memories_for_agent(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=kind,
            )

        result = benchmark("Memory Recall (by kind)", recall_by_kind, iterations=200)
        print(f"\n{result}")

        # Assert reasonable filter performance (< 5ms)
        assert result.mean_ms < 5, f"Recall by kind too slow: {result.mean_ms:.2f}ms"

    def test_memory_search(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Full-text search across memories."""
        # Create searchable memories
        topics = ["python", "testing", "performance", "memory", "database"]
        for i in range(200):
            topic = topics[i % len(topics)]
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content=f"Learning about {topic}: Important details for topic {i}",
                impact=ImpactLevel.MEDIUM,
            )
            store.save_memory(memory)

        counter = [0]

        def search_memories():
            topic = topics[counter[0] % len(topics)]
            counter[0] += 1
            store.search_memories(agent_id=agent.id, query=topic, project_id=project.id)

        result = benchmark("Memory Search (full-text)", search_memories, iterations=200)
        print(f"\n{result}")

        # Assert reasonable search performance (< 10ms)
        assert result.mean_ms < 10, f"Search too slow: {result.mean_ms:.2f}ms"

    def test_injection_small_set(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Inject memories (small set, under budget)."""
        # Create 20 memories (typical small project)
        # Note: token_count is calculated on save, simulating real usage
        for i in range(20):
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content=f"Learning {i}: " + "x" * 100,  # ~100 chars each
                impact=ImpactLevel.MEDIUM,
            )
            ensure_token_count(memory)  # Pre-calculate like real save
            store.save_memory(memory)

        injector = MemoryInjector(store)

        def inject():
            injector.inject(agent, project)

        result = benchmark("Injection (20 memories)", inject, iterations=100)
        print(f"\n{result}")

        # Token caching eliminates tiktoken overhead during injection
        # Remaining cost is save_memory() to update last_accessed (~4ms per memory)
        # 20 memories × 4ms = ~80ms, allow some variance
        assert result.mean_ms < 150, f"Injection too slow: {result.mean_ms:.2f}ms"

    def test_injection_large_set(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Inject memories (large set, budget-constrained)."""
        # Create 500 memories (stress test)
        # Note: token_count is calculated on save, simulating real usage
        for i in range(500):
            impact = [
                ImpactLevel.LOW,
                ImpactLevel.MEDIUM,
                ImpactLevel.HIGH,
                ImpactLevel.CRITICAL,
            ][i % 4]
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content=f"Learning {i}: " + "x" * 200,  # ~200 chars each
                impact=impact,
            )
            ensure_token_count(memory)  # Pre-calculate like real save
            store.save_memory(memory)

        injector = MemoryInjector(store)

        def inject():
            injector.inject(agent, project)

        result = benchmark(
            "Injection (500 memories, budget-limited)", inject, iterations=50
        )
        stats = injector.get_stats(agent, project)
        print(f"\n{result}")
        print(
            f"  Total memories: {stats['total']} | Budget: {stats['budget_tokens']} tokens"
        )

        # With 500 memories, ~80-100 fit in budget before hitting 20k tokens
        # Each injected memory triggers save_memory() for last_accessed update
        # Plus the accumulating memory count grows each iteration
        # Assert < 4 seconds for stress test (previous was ~3s with tiktoken)
        assert (
            result.mean_ms < 4000
        ), f"Large injection too slow: {result.mean_ms:.2f}ms"

    def test_decay_processing(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """Benchmark: Process decay on memories."""
        # Create 100 memories with various impacts
        from datetime import datetime, timedelta

        impacts = [ImpactLevel.LOW, ImpactLevel.MEDIUM, ImpactLevel.HIGH]
        for i in range(100):
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content=f"Learning {i}: Some content that may decay over time.",
                impact=impacts[i % len(impacts)],
            )
            # Backdate some memories
            memory.created_at = datetime.now() - timedelta(days=i % 30)
            store.save_memory(memory)

        decay = MemoryDecay(store)

        def process_decay():
            decay.process_decay(agent.id, project.id)

        result = benchmark(
            "Decay Processing (100 memories)", process_decay, iterations=50
        )
        print(f"\n{result}")

        # Assert reasonable decay time (< 50ms)
        assert result.mean_ms < 50, f"Decay processing too slow: {result.mean_ms:.2f}ms"

    def test_signature_creation(self, agent: Agent) -> None:
        """Benchmark: Sign a memory."""
        assert agent.signing_key is not None
        signing_key = agent.signing_key

        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="A memory to be signed for performance testing.",
            impact=ImpactLevel.MEDIUM,
        )

        def sign():
            sign_memory(memory, signing_key)

        result = benchmark("Signature Creation", sign, iterations=1000)
        print(f"\n{result}")

        # Assert very fast signing (< 0.1ms)
        assert result.mean_ms < 0.1, f"Signing too slow: {result.mean_ms:.3f}ms"

    def test_signature_verification(self, agent: Agent) -> None:
        """Benchmark: Verify a memory signature."""
        assert agent.signing_key is not None
        signing_key = agent.signing_key

        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="A signed memory for verification testing.",
            impact=ImpactLevel.MEDIUM,
        )
        memory.signature = sign_memory(memory, signing_key)

        def verify():
            verify_signature(memory, signing_key)

        result = benchmark("Signature Verification", verify, iterations=1000)
        print(f"\n{result}")

        # Assert very fast verification (< 0.1ms)
        assert result.mean_ms < 0.1, f"Verification too slow: {result.mean_ms:.3f}ms"

    def test_full_session_simulation(
        self, store: MemoryStore, agent: Agent, project: Project
    ) -> None:
        """
        Benchmark: Simulate a full session workflow.

        This simulates what happens during a typical session:
        1. Load existing memories (injection)
        2. Create a few new memories
        3. Process decay
        4. Sign new memories
        """
        assert agent.signing_key is not None
        signing_key = agent.signing_key

        # Pre-populate with 50 existing memories (with cached token counts)
        for i in range(50):
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content=f"Existing memory {i}: Background context.",
                impact=ImpactLevel.MEDIUM,
            )
            memory.signature = sign_memory(memory, signing_key)
            ensure_token_count(memory)  # Pre-calculate like real save
            store.save_memory(memory)

        injector = MemoryInjector(store)
        decay = MemoryDecay(store)
        counter = [0]

        def full_session():
            counter[0] += 1

            # 1. Inject memories (session start)
            injector.inject(agent, project)

            # 2. Create 3 new memories (typical session)
            # Note: This includes tiktoken cost for new memories
            new_memories = []
            for i in range(3):
                memory = Memory(
                    agent_id=agent.id,
                    region=RegionType.PROJECT,
                    project_id=project.id,
                    kind=MemoryKind.LEARNINGS,
                    content=f"Session {counter[0]} memory {i}: New learning.",
                    impact=ImpactLevel.MEDIUM,
                )
                memory.signature = sign_memory(memory, signing_key)
                ensure_token_count(memory)  # This has tiktoken cost
                store.save_memory(memory)
                new_memories.append(memory)

            # 3. Process decay
            decay.process_decay(agent.id, project.id)

        result = benchmark(
            "Full Session Simulation", full_session, iterations=30, warmup=3
        )
        print(f"\n{result}")

        # Full session includes:
        # - Injection (50+ memories, each saved for last_accessed update)
        # - 3 new memory creates (with tiktoken for token counting)
        # - Decay processing
        # The save operations dominate; typical is 500-700ms
        assert result.mean_ms < 1000, f"Full session too slow: {result.mean_ms:.2f}ms"


class TestPerformanceSummary:
    """Generate a performance summary report."""

    def test_generate_summary(self, tmp_path: Path) -> None:
        """Generate and print a comprehensive performance summary."""
        store = MemoryStore(db_path=tmp_path / "summary_test.db", limits=NO_LIMITS)
        agent = Agent(id="summary-agent", name="SummaryAgent", signing_key="key-123")
        project = Project(
            id="summary-project", name="SummaryProject", path=Path("/tmp")
        )
        store.save_agent(agent)
        store.save_project(project)

        results: list[BenchmarkResult] = []

        # Memory creation
        def create_memory():
            memory = Memory(
                agent_id=agent.id,
                region=RegionType.PROJECT,
                project_id=project.id,
                kind=MemoryKind.LEARNINGS,
                content="Test memory for summary",
                impact=ImpactLevel.MEDIUM,
            )
            store.save_memory(memory)

        results.append(benchmark("Create Memory", create_memory, iterations=100))

        # Memory recall
        memories = store.get_memories_for_agent(
            agent_id=agent.id, region=RegionType.PROJECT, project_id=project.id
        )
        if memories:
            test_id = memories[0].id

            def recall():
                store.get_memory(test_id)

            results.append(benchmark("Recall by ID", recall, iterations=200))

        # Injection
        injector = MemoryInjector(store)

        def inject():
            injector.inject(agent, project)

        results.append(benchmark("Inject Memories", inject, iterations=50))

        # Decay
        decay = MemoryDecay(store)

        def process():
            decay.process_decay(agent.id, project.id)

        results.append(benchmark("Process Decay", process, iterations=50))

        # Signing
        assert agent.signing_key is not None
        signing_key = agent.signing_key

        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="Sign test",
            impact=ImpactLevel.LOW,
        )

        def sign():
            sign_memory(memory, signing_key)

        results.append(benchmark("Sign Memory", sign, iterations=500))

        # Print summary
        print("\n" + "=" * 60)
        print("LTM PERFORMANCE SUMMARY")
        print("=" * 60)

        for r in results:
            print(f"\n{r.name}:")
            print(
                f"  Mean: {r.mean_ms:.3f}ms | Throughput: {r.ops_per_sec:.0f} ops/sec"
            )

        print("\n" + "=" * 60)
        print("VERDICT: ", end="")

        # Check operations against their specific thresholds
        # Injection is known to be slow due to tiktoken (optimization target)
        thresholds = {
            "Create Memory": 20,
            "Recall by ID": 5,
            "Inject Memories": 1000,  # tiktoken overhead - optimization target
            "Process Decay": 50,
            "Sign Memory": 1,
        }

        slow_ops = []
        for r in results:
            threshold = thresholds.get(r.name, 50)
            if r.mean_ms >= threshold:
                slow_ops.append(f"{r.name} ({r.mean_ms:.0f}ms > {threshold}ms)")

        if not slow_ops:
            print("PASS - All operations within acceptable limits")
        else:
            print(f"REVIEW - Slow operations: {', '.join(slow_ops)}")

        print("=" * 60)

        # Don't fail the test - this is informational
        # The individual tests have appropriate thresholds
