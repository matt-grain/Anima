"""Profile storage and injection hotspots.

Run with:
    uv run python scripts/profile_storage_injection.py

Produces a small pstats summary to stdout and writes `profile_stats.prof` in the repo root.
"""

import cProfile
import pstats
import tempfile
from pathlib import Path
import time

from anima.core import Agent, Project, Memory, RegionType, MemoryKind, ImpactLevel
from anima.lifecycle.injection import ensure_token_count, MemoryInjector
from anima.storage import MemoryStore


def setup_store(tmpdir: Path, num_memories: int = 500) -> tuple[MemoryStore, Agent, Project]:
    store = MemoryStore(db_path=tmpdir / "perf.db")
    agent = Agent(id="perf-agent", name="PerfAgent", signing_key="perf-key-123")
    store.save_agent(agent)
    project = Project(id="perf-project", name="PerfProject", path=Path("/tmp/perf"))
    store.save_project(project)

    for i in range(num_memories):
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
            content=f"Learning {i}: " + "x" * 200,
            impact=impact,
        )
        ensure_token_count(memory)
        store.save_memory(memory)

    return store, agent, project


def profile_run():
    tmpdir = Path(tempfile.mkdtemp(prefix="ltm-perf-"))
    store, agent, project = setup_store(tmpdir, num_memories=500)
    injector = MemoryInjector(store)

    def work():
        # stress injection and a couple of queries
        injector.inject(agent, project)
        store.get_memories_for_agent(agent.id, region=RegionType.PROJECT, project_id=project.id)
        store.search_memories(agent.id, "performance", project_id=project.id)

    prof = cProfile.Profile()
    prof.runcall(work)
    prof.dump_stats("profile_stats.prof")

    stats = pstats.Stats(prof).sort_stats("cumulative")
    print("\nTop 20 by cumulative time:\n")
    stats.print_stats(20)

    # Quick micro-benchmarks
    print("\nMicro timings:\n")
    t0 = time.perf_counter()
    for _ in range(100):
        mem = Memory(
            agent_id=agent.id,
            region=RegionType.PROJECT,
            project_id=project.id,
            kind=MemoryKind.LEARNINGS,
            content="Short test",
            impact=ImpactLevel.LOW,
        )
        store.save_memory(mem)
    t1 = time.perf_counter()
    print(f"100 save_memory calls in {(t1 - t0) * 1000:.2f}ms")


if __name__ == "__main__":
    profile_run()
