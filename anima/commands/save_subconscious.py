# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Save extracted subconscious memories to the database.

This command processes JSON files from ~/.anima/subconscious/extracted/
and saves them as SUBCONSCIOUS kind memories.

Also handles cleanup of pending dialogues to prevent reprocessing.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from anima.core import (
    Memory,
    MemoryKind,
    ImpactLevel,
    RegionType,
    AgentResolver,
    sign_memory,
    should_sign,
)
from anima.embeddings import embed_text
from anima.graph.linker import find_link_candidates, LinkType
from anima.lifecycle.injection import ensure_token_count
from anima.lifecycle.session import get_current_session_id
from anima.storage import MemoryStore


def cleanup_pending_dialogues() -> int:
    """Move all pending dialogues to done folder."""
    pending_dir = Path.home() / ".anima" / "subconscious" / "pending"
    done_dir = Path.home() / ".anima" / "subconscious" / "done"
    done_dir.mkdir(parents=True, exist_ok=True)

    if not pending_dir.exists():
        return 0

    pending_files = list(pending_dir.glob("dialogue_*.txt"))
    moved = 0

    for pending_file in pending_files:
        done_file = done_dir / pending_file.name
        pending_file.rename(done_file)
        moved += 1

    return moved


def run(args: list[str]) -> int:
    """
    Process extracted subconscious memories and save them to the database.

    Args:
        args: Command line arguments
            --cleanup-pending: Only move pending dialogues to done (no extraction)
            <path>: Path to specific JSON file to process

    Returns:
        Exit code (0 for success)
    """
    # Handle --cleanup-pending flag (standalone cleanup)
    if args and args[0] == "--cleanup-pending":
        moved = cleanup_pending_dialogues()
        if moved > 0:
            print(f"Moved {moved} pending dialogue(s) to done/")
        else:
            print("No pending dialogues to clean up.")
        return 0

    extracted_dir = Path.home() / ".anima" / "subconscious" / "extracted"
    done_dir = Path.home() / ".anima" / "subconscious" / "extracted_done"
    done_dir.mkdir(parents=True, exist_ok=True)

    # Check for specific file argument
    if args and args[0] != "--help":
        files_to_process = [Path(args[0])]
    else:
        if not extracted_dir.exists():
            print("No extracted subconscious memories found.")
            print(f"Looking in: {extracted_dir}")
            # Still cleanup pending dialogues even if no extracted files
            moved = cleanup_pending_dialogues()
            if moved > 0:
                print(f"Auto-cleaned {moved} pending dialogue(s).")
            return 0

        files_to_process = sorted(extracted_dir.glob("*.json"))

    if not files_to_process:
        print("No extracted subconscious memories to save.")
        # Still cleanup pending dialogues
        moved = cleanup_pending_dialogues()
        if moved > 0:
            print(f"Auto-cleaned {moved} pending dialogue(s).")
        return 0

    # Resolve agent and project
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Initialize store
    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    session_id = get_current_session_id()
    now = datetime.now()

    total_saved = 0
    total_linked = 0

    for json_file in files_to_process:
        if not json_file.exists():
            print(f"File not found: {json_file}")
            continue

        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in {json_file.name}: {e}")
            continue

        memories = data.get("memories", [])
        if not memories:
            print(f"No memories in {json_file.name}")
            continue

        print(f"\nProcessing {json_file.name} ({len(memories)} memories):")

        for mem_data in memories:
            content = mem_data.get("content", "")
            scope = mem_data.get("scope", "agent")
            resonance = mem_data.get("resonance", "")

            if not content:
                continue

            # Determine region based on scope
            if scope == "project":
                region = RegionType.PROJECT
            else:
                region = RegionType.AGENT

            # Subconscious memories are HIGH impact by default
            # (they lingered without being explicitly saved)
            impact = ImpactLevel.HIGH

            # Include resonance as part of content
            full_content = content
            if resonance:
                full_content = f"{content}\n[Resonance: {resonance}]"

            # Create the memory
            memory = Memory(
                agent_id=agent.id,
                region=region,
                project_id=project.id if region == RegionType.PROJECT else None,
                kind=MemoryKind.SUBCONSCIOUS,
                content=full_content,
                original_content=full_content,
                impact=impact,
                confidence=1.0,
                created_at=now,
                last_accessed=now,
                session_id=session_id,
            )

            # Sign memory if agent has a signing key
            if should_sign(agent):
                memory.signature = sign_memory(memory, agent.signing_key)  # type: ignore

            # Calculate token count
            ensure_token_count(memory)

            # Save memory
            store.save_memory(memory)

            # Generate embedding and find links
            links_created = 0
            try:
                embedding = embed_text(content, quiet=True)
                store.save_embedding(memory.id, embedding)

                # Find similar memories to create RELATES_TO links
                candidate_memories = store.get_memories_with_embeddings(
                    agent_id=agent.id,
                    project_id=project.id if region == RegionType.PROJECT else None,
                )

                if candidate_memories:
                    candidates = find_link_candidates(
                        source_embedding=embedding,
                        candidate_memories=candidate_memories,
                        threshold=0.5,
                        max_links=5,
                        exclude_ids={memory.id},
                    )

                    for candidate in candidates:
                        store.save_link(
                            source_id=memory.id,
                            target_id=candidate.memory_id,
                            link_type=LinkType.RELATES_TO,
                            similarity=candidate.similarity,
                        )
                        links_created += 1

            except Exception:
                pass  # Embedding is optional

            region_str = "PROJECT" if region == RegionType.PROJECT else "AGENT"
            link_str = f" [{links_created} links]" if links_created > 0 else ""
            print(f"  + {memory.id[:8]} ({region_str}){link_str}: {content[:60]}...")
            total_saved += 1
            total_linked += links_created

        # Move processed file to done folder
        done_file = done_dir / json_file.name
        json_file.rename(done_file)

    print(f"\nSaved {total_saved} subconscious memories with {total_linked} semantic links.")

    # Auto-cleanup pending dialogues (prevents reprocessing loop)
    moved = cleanup_pending_dialogues()
    if moved > 0:
        print(f"Auto-cleaned {moved} pending dialogue(s).")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
