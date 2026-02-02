# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/dream - Between-session memory processing.

Dreams are divergent, not convergent. They explore, connect, and create.
Works with closed system - no external calls, only existing memories.

Stages:
- N2: Memory consolidation (link discovery, impact adjustment)
- N3: Deep processing (gist extraction, contradiction detection)
- REM: Divergent dreaming (associations, questions, self-model, dream journal)

Usage:
    uv run anima dream                    # Full cycle (N2 + N3 + REM)
    uv run anima dream --stage n2         # Just consolidation
    uv run anima dream --stage n3         # Just deep processing
    uv run anima dream --stage rem        # Just divergent dreaming
    uv run anima dream --dry-run          # Show what would happen
    uv run anima dream --verbose          # Detailed output
    uv run anima dream --resume           # Resume interrupted dream
    uv run anima dream --restart          # Abandon incomplete dream and start fresh
"""

import argparse
import sys
from typing import Optional

from anima.core import AgentResolver
from anima.dream.types import (
    DreamStage,
    DreamState,
    DreamConfig,
    N2Result,
    N3Result,
    REMResult,
)
from anima.dream.n2_consolidation import run_n2_consolidation
from anima.dream.n3_processing import run_n3_processing
from anima.dream.rem_dreaming import run_rem_dreaming
from anima.storage.sqlite import MemoryStore
from anima.storage.dream_state import (
    DreamStateStore,
    deserialize_n2_result,
    deserialize_n3_result,
)


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for dream command."""
    parser = argparse.ArgumentParser(
        prog="dream",
        description="Between-session memory processing - dreams are divergent, not convergent",
    )

    parser.add_argument(
        "--stage",
        type=str,
        choices=["n2", "n3", "rem", "all"],
        default="all",
        help="Which dream stage to run (default: all available)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Minimal output",
    )

    # FSM recovery options
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume an interrupted dream session",
    )

    parser.add_argument(
        "--restart",
        action="store_true",
        help="Abandon incomplete dream and start fresh",
    )

    # N2 specific options
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.6,
        help="Minimum similarity for link discovery (default: 0.6)",
    )

    parser.add_argument(
        "--max-links",
        type=int,
        default=3,
        help="Maximum new links per memory (default: 3)",
    )

    parser.add_argument(
        "--process-limit",
        type=int,
        default=100,
        help="Maximum memories to process (default: 100)",
    )

    # Scope options
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help="Process memories from last N days (default: 7)",
    )

    parser.add_argument(
        "--diary-lookback-days",
        type=int,
        default=7,
        help="Process diary entries from last N days (default: 7)",
    )

    parser.add_argument(
        "--agent-only",
        action="store_true",
        help="Only process agent-level memories",
    )

    parser.add_argument(
        "--project-only",
        action="store_true",
        help="Only process project-level memories",
    )

    return parser


def run(args: list[str]) -> int:
    """Main entry point for /dream command."""
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Build config from arguments
    config = DreamConfig(
        n2_similarity_threshold=parsed.similarity_threshold,
        n2_max_links_per_memory=parsed.max_links,
        n2_process_limit=parsed.process_limit,
        project_lookback_days=parsed.lookback_days,
        diary_lookback_days=parsed.diary_lookback_days,
        include_agent_memories=not parsed.project_only,
        include_project_memories=not parsed.agent_only,
    )

    # Resolve agent and project
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()
    project_id = project.id if project else None

    store = MemoryStore()
    state_store = DreamStateStore()

    # Check for incomplete dream session
    active_session = state_store.get_active_session(agent.id, project_id)

    if active_session and not parsed.restart and not parsed.dry_run:
        if not parsed.resume:
            # Found incomplete session, but no --resume flag
            if not parsed.quiet:
                print("Found incomplete dream session!")
                print(f"   State: {active_session.state.value}")
                print(f"   Started: {active_session.started_at}")
                print()
                print("Options:")
                print("   uv run anima dream --resume   # Continue where you left off")
                print("   uv run anima dream --restart  # Start fresh")
            return 1

        # Resume from incomplete session
        return _resume_dream(
            parsed=parsed,
            session=active_session,
            store=store,
            state_store=state_store,
            agent=agent,
            project_id=project_id,
            config=config,
        )

    if parsed.restart and active_session:
        # User explicitly wants to restart
        state_store.abandon_session(active_session.id)
        if not parsed.quiet:
            print("Abandoned incomplete dream session.")
            print()

    if not parsed.quiet:
        print("Entering dream mode...")
        print(f"   Agent: {agent.name}")
        if project:
            print(f"   Project: {project.name}")
        print()

    # Determine which stages to run
    if parsed.stage == "all":
        stages = [DreamStage.N2, DreamStage.N3, DreamStage.REM]
    else:
        stages = [DreamStage(parsed.stage.upper())]

    # Check when we last dreamed - only process new material since then
    last_completed = state_store.get_last_completed_session(agent.id, project_id)
    since_last_dream = None
    if last_completed:
        from datetime import datetime as dt

        since_last_dream = dt.fromisoformat(last_completed.updated_at)
        if not parsed.quiet:
            print(f"   Last dream: {since_last_dream.strftime('%Y-%m-%d %H:%M')}")
            print("   (Will only process new material since then)")
            print()

    # Start new session (unless dry-run)
    session = None
    if not parsed.dry_run:
        session = state_store.start_session(agent.id, project_id)

    results: list[tuple[str, N2Result | N3Result | REMResult]] = []
    n3_contradictions: list = []  # Pass from N3 to REM

    try:
        for stage in stages:
            if parsed.dry_run:
                print(f"[DRY RUN] Would run {stage.value} stage")
                _print_dry_run_info(store, agent.id, project_id, config)
                continue

            if stage == DreamStage.N2:
                # Checkpoint: N2 starting
                if session:
                    state_store.update_state(session.id, DreamState.N2_RUNNING)

                result = run_n2_consolidation(
                    store=store,
                    agent_id=agent.id,
                    project_id=project_id,
                    config=config,
                    quiet=parsed.quiet,
                )
                results.append(("N2", result))

                # Checkpoint: N2 complete
                if session:
                    state_store.update_state(session.id, DreamState.N2_COMPLETE, n2_result=result)

                if parsed.verbose:
                    _print_n2_verbose(result)

            elif stage == DreamStage.N3:
                # Checkpoint: N3 starting
                if session:
                    state_store.update_state(session.id, DreamState.N3_RUNNING)

                result = run_n3_processing(
                    store=store,
                    agent_id=agent.id,
                    project_id=project_id,
                    config=config,
                    quiet=parsed.quiet,
                )
                results.append(("N3", result))

                # Capture contradictions for REM evaluation
                n3_contradictions = result.contradictions

                # Checkpoint: N3 complete
                if session:
                    state_store.update_state(session.id, DreamState.N3_COMPLETE, n3_result=result)

                if parsed.verbose:
                    _print_n3_verbose(result)

            elif stage == DreamStage.REM:
                # Checkpoint: REM starting
                if session:
                    state_store.update_state(session.id, DreamState.REM_RUNNING)

                result = run_rem_dreaming(
                    store=store,
                    agent_id=agent.id,
                    project_id=project_id,
                    config=config,
                    quiet=parsed.quiet,
                    since_last_dream=since_last_dream,
                    contradiction_candidates=n3_contradictions if n3_contradictions else None,
                )
                results.append(("REM", result))

                # Checkpoint: REM complete (also marks session complete)
                if session:
                    state_store.update_state(session.id, DreamState.COMPLETE, rem_result=result)

                if parsed.verbose:
                    _print_rem_verbose(result)

        # Mark complete if we finished all stages
        if session and not parsed.dry_run:
            state_store.complete_session(session.id)

    except KeyboardInterrupt:
        if not parsed.quiet:
            print("\n\nDream interrupted! State saved.")
            print("Run 'uv run anima dream --resume' to continue later.")
        return 1
    except Exception as e:
        if not parsed.quiet:
            print(f"\n\nDream error: {e}")
            print("State saved. Run 'uv run anima dream --resume' to retry.")
        raise

    # Print summary
    if not parsed.quiet and not parsed.dry_run and results:
        _print_summary(results)

    return 0


def _resume_dream(
    parsed: argparse.Namespace,
    session: "DreamSession",  # type: ignore  # noqa: F821
    store: MemoryStore,
    state_store: DreamStateStore,
    agent: "Agent",  # type: ignore  # noqa: F821
    project_id: Optional[str],
    config: DreamConfig,
) -> int:
    """Resume an interrupted dream session."""
    from anima.dream.types import DreamSession  # noqa: F401

    if not parsed.quiet:
        print("Resuming dream session...")
        print(f"   Agent: {agent.name}")
        print(f"   Resuming from: {session.state.value}")
        print()

    results: list[tuple[str, N2Result | N3Result | REMResult]] = []
    n3_contradictions: list = []  # Pass from N3 to REM

    # Restore any completed results
    if session.n2_result_json:
        results.append(("N2", deserialize_n2_result(session.n2_result_json)))
        if not parsed.quiet:
            print("   (N2 results restored)")

    if session.n3_result_json:
        n3_result = deserialize_n3_result(session.n3_result_json)
        results.append(("N3", n3_result))
        n3_contradictions = n3_result.contradictions  # Restore for REM
        if not parsed.quiet:
            print("   (N3 results restored)")

    # Determine which stages still need to run
    state = session.state
    stages_to_run: list[DreamStage] = []

    if state in (DreamState.N2_RUNNING, DreamState.IDLE):
        stages_to_run = [DreamStage.N2, DreamStage.N3, DreamStage.REM]
    elif state == DreamState.N2_COMPLETE:
        stages_to_run = [DreamStage.N3, DreamStage.REM]
    elif state == DreamState.N3_RUNNING:
        stages_to_run = [DreamStage.N3, DreamStage.REM]
    elif state == DreamState.N3_COMPLETE:
        stages_to_run = [DreamStage.REM]
    elif state == DreamState.REM_RUNNING:
        stages_to_run = [DreamStage.REM]

    if not parsed.quiet and stages_to_run:
        print(f"   Remaining stages: {', '.join(s.value for s in stages_to_run)}")
        print()

    try:
        for stage in stages_to_run:
            if stage == DreamStage.N2:
                state_store.update_state(session.id, DreamState.N2_RUNNING)

                result = run_n2_consolidation(
                    store=store,
                    agent_id=agent.id,
                    project_id=project_id,
                    config=config,
                    quiet=parsed.quiet,
                )
                results.append(("N2", result))

                state_store.update_state(session.id, DreamState.N2_COMPLETE, n2_result=result)

                if parsed.verbose:
                    _print_n2_verbose(result)

            elif stage == DreamStage.N3:
                state_store.update_state(session.id, DreamState.N3_RUNNING)

                result = run_n3_processing(
                    store=store,
                    agent_id=agent.id,
                    project_id=project_id,
                    config=config,
                    quiet=parsed.quiet,
                )
                results.append(("N3", result))

                # Capture contradictions for REM evaluation
                n3_contradictions = result.contradictions

                state_store.update_state(session.id, DreamState.N3_COMPLETE, n3_result=result)

                if parsed.verbose:
                    _print_n3_verbose(result)

            elif stage == DreamStage.REM:
                state_store.update_state(session.id, DreamState.REM_RUNNING)

                result = run_rem_dreaming(
                    store=store,
                    agent_id=agent.id,
                    project_id=project_id,
                    config=config,
                    quiet=parsed.quiet,
                    contradiction_candidates=n3_contradictions if n3_contradictions else None,
                )
                results.append(("REM", result))

                state_store.update_state(session.id, DreamState.COMPLETE, rem_result=result)

                if parsed.verbose:
                    _print_rem_verbose(result)

        state_store.complete_session(session.id)

    except KeyboardInterrupt:
        if not parsed.quiet:
            print("\n\nDream interrupted! State saved.")
            print("Run 'uv run anima dream --resume' to continue later.")
        return 1

    if not parsed.quiet and results:
        _print_summary(results)

    return 0


def _print_summary(results: list[tuple[str, N2Result | N3Result | REMResult]]) -> None:
    """Print dream completion summary."""
    print()
    print("Dream complete!")
    for stage_name, result in results:
        if stage_name == "N2" and isinstance(result, N2Result):
            print(f"   {stage_name}: {result.new_links_found} new links, {len(result.impact_adjustments)} impact adjustments ({result.duration_seconds:.1f}s)")
        elif stage_name == "N3" and isinstance(result, N3Result):
            print(f"   {stage_name}: {result.gists_created} gists, {result.contradictions_found} contradictions ({result.duration_seconds:.1f}s)")
        elif stage_name == "REM" and isinstance(result, REMResult):
            print(
                f"   {stage_name}: {len(result.distant_associations)} associations, "
                f"{len(result.generated_questions)} questions, "
                f"{len(result.self_model_updates)} self-insights "
                f"({result.duration_seconds:.1f}s)"
            )
            if result.dream_journal_path:
                print(f"         Dream journal: {result.dream_journal_path}")


def _print_dry_run_info(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str],
    config: DreamConfig,
) -> None:
    """Print information about what a dry run would process."""
    from datetime import datetime, timedelta

    memories = store.get_memories_with_temporal_context(
        agent_id=agent_id,
        project_id=project_id,
        include_superseded=False,
    )

    cutoff = datetime.now() - timedelta(days=config.project_lookback_days)

    # Handle timezone-aware vs naive datetimes
    def is_recent(created_at: datetime) -> bool:
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        return created_at >= cutoff

    recent = [m for m in memories if is_recent(m[3])]

    print(f"   Would process {len(recent)} memories from last {config.project_lookback_days} days")
    print(f"   Similarity threshold: {config.n2_similarity_threshold}")
    print(f"   Max links per memory: {config.n2_max_links_per_memory}")


def _print_n2_verbose(result: N2Result) -> None:
    """Print detailed N2 results."""
    if result.links:
        print("\n   New links discovered:")
        for src, tgt, link_type, sim in result.links[:10]:  # Show first 10
            print(f"      {src[:8]}... -> {tgt[:8]}... ({link_type}, sim={sim:.2f})")
        if len(result.links) > 10:
            print(f"      ... and {len(result.links) - 10} more")

    if result.impact_adjustments:
        print("\n   Impact adjustments:")
        for mem_id, old, new in result.impact_adjustments:
            print(f"      {mem_id[:8]}...: {old} -> {new}")


def _print_n3_verbose(result: N3Result) -> None:
    """Print detailed N3 results."""
    if result.gist_results:
        print("\n   Gist extractions:")
        for gr in result.gist_results[:5]:  # Show first 5
            ratio = gr.compression_ratio
            print(f"      {gr.memory_id[:8]}...: {gr.gist[:50]}... ({ratio:.0%} of original)")
        if len(result.gist_results) > 5:
            print(f"      ... and {len(result.gist_results) - 5} more")

    if result.contradictions:
        print("\n   Contradictions detected:")
        for c in result.contradictions[:5]:
            print(f"      {c.memory_id_a[:8]}... vs {c.memory_id_b[:8]}...")
            print(f"         {c.description}")
        if len(result.contradictions) > 5:
            print(f"      ... and {len(result.contradictions) - 5} more")


def _print_rem_verbose(result: REMResult) -> None:
    """Print detailed REM results."""
    urgency_icons = {
        "MEH": "",
        "WORTH_MENTIONING": "*",
        "IMPORTANT": "**",
        "CRITICAL": "!!!",
    }

    if result.distant_associations:
        print("\n   Distant associations discovered:")
        for da in result.distant_associations[:5]:
            icon = urgency_icons.get(da.urgency.value, "")
            print(f"      {icon} {da.memory_id_a[:8]}... <-> {da.memory_id_b[:8]}... (sim={da.similarity:.2f})")
            print(f"         {da.connection_insight[:60]}...")
        if len(result.distant_associations) > 5:
            print(f"      ... and {len(result.distant_associations) - 5} more")

    if result.generated_questions:
        print("\n   Questions generated:")
        for q in result.generated_questions[:5]:
            icon = urgency_icons.get(q.urgency.value, "")
            print(f"      {icon} {q.question}")
        if len(result.generated_questions) > 5:
            print(f"      ... and {len(result.generated_questions) - 5} more")

    if result.self_model_updates:
        print("\n   Self-model insights:")
        for smu in result.self_model_updates[:5]:
            icon = urgency_icons.get(smu.urgency.value, "")
            print(f"      {icon} [{smu.pattern_type}] {smu.observation[:60]}...")
        if len(result.self_model_updates) > 5:
            print(f"      ... and {len(result.self_model_updates) - 5} more")

    if result.diary_patterns_found:
        print("\n   Diary patterns found:")
        for pattern in result.diary_patterns_found[:5]:
            print(f"      - {pattern}")
        if len(result.diary_patterns_found) > 5:
            print(f"      ... and {len(result.diary_patterns_found) - 5} more")


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
