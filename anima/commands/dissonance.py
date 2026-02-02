# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/dissonance - View and resolve cognitive dissonances.

N3 dream processing detects contradiction *candidates* based on heuristics.
During REM lucid dreaming, the agent evaluates which are real contradictions.
Only confirmed contradictions are stored here for human help.

Usage:
    uv run anima dissonance              # List open dissonances
    uv run anima dissonance --all        # Include resolved/dismissed
    uv run anima dissonance show ID      # Show details with memory content
    uv run anima dissonance add MEM_A MEM_B 'description'  # Add confirmed contradiction
    uv run anima dissonance resolve ID 'explanation'  # Mark as resolved
    uv run anima dissonance dismiss ID   # Dismiss (false positive)
"""

import argparse
import sys

from anima.core import AgentResolver
from anima.storage.dissonance import DissonanceStore, DissonanceStatus
from anima.storage.sqlite import MemoryStore


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for dissonance command."""
    parser = argparse.ArgumentParser(
        prog="dissonance",
        description="View and resolve cognitive dissonances (contradictions needing human help)",
    )

    subparsers = parser.add_subparsers(dest="action", help="Action to perform")

    # List (default)
    list_parser = subparsers.add_parser("list", help="List dissonances")
    list_parser.add_argument("--all", "-a", action="store_true", help="Include resolved/dismissed")

    # Resolve
    resolve_parser = subparsers.add_parser("resolve", help="Mark dissonance as resolved")
    resolve_parser.add_argument("id", type=str, help="Dissonance ID")
    resolve_parser.add_argument("resolution", type=str, nargs="?", help="How it was resolved")

    # Dismiss
    dismiss_parser = subparsers.add_parser("dismiss", help="Dismiss (not a real contradiction)")
    dismiss_parser.add_argument("id", type=str, help="Dissonance ID")

    # Show details
    show_parser = subparsers.add_parser("show", help="Show dissonance details with memory content")
    show_parser.add_argument("id", type=str, help="Dissonance ID")

    # Add confirmed contradiction (used by agent during dream evaluation)
    add_parser = subparsers.add_parser("add", help="Add a confirmed contradiction")
    add_parser.add_argument("memory_a", type=str, help="First memory ID (partial OK)")
    add_parser.add_argument("memory_b", type=str, help="Second memory ID (partial OK)")
    add_parser.add_argument("description", type=str, help="Why this is a contradiction")

    # Global options
    parser.add_argument("--all", "-a", action="store_true", help="Include resolved/dismissed (for list)")

    return parser


def run(args: list[str]) -> int:
    """Main entry point for /dissonance command."""
    parser = create_parser()

    # Handle default action (list)
    if not args or (args and args[0] not in ["list", "resolve", "dismiss", "show", "add"]):
        # Prepend "list" for default behavior
        if args and not args[0].startswith("-"):
            # Might be trying to show a specific ID
            args = ["show"] + args
        else:
            args = ["list"] + args

    parsed = parser.parse_args(args)

    resolver = AgentResolver()
    agent = resolver.resolve()
    store = DissonanceStore()
    memory_store = MemoryStore()

    if parsed.action == "list":
        return _list_dissonances(store, agent.id, include_all=parsed.all)

    elif parsed.action == "show":
        return _show_dissonance(store, memory_store, parsed.id)

    elif parsed.action == "resolve":
        resolution = parsed.resolution
        if not resolution:
            print("Please provide a resolution explanation.")
            print("Usage: uv run anima dissonance resolve ID 'How I resolved it'")
            return 1
        return _resolve_dissonance(store, parsed.id, resolution)

    elif parsed.action == "dismiss":
        return _dismiss_dissonance(store, parsed.id)

    elif parsed.action == "add":
        return _add_dissonance(store, memory_store, agent.id, parsed.memory_a, parsed.memory_b, parsed.description)

    return 0


def _list_dissonances(store: DissonanceStore, agent_id: str, include_all: bool = False) -> int:
    """List dissonances for the agent."""
    dissonances = store.get_open_dissonances(agent_id)

    if not dissonances and not include_all:
        print("No open dissonances. Your memories are consistent!")
        print("(Run with --all to see resolved/dismissed)")
        return 0

    print("Cognitive Dissonances (contradictions needing resolution)")
    print("=" * 60)
    print()

    status_icons = {
        DissonanceStatus.OPEN: "❓",
        DissonanceStatus.RESOLVED: "✅",
        DissonanceStatus.DISMISSED: "🚫",
    }

    for d in dissonances:
        icon = status_icons.get(d.status, "?")
        print(f"{icon} [{d.id}] {d.status.value}")
        print(f"   Detected: {d.detected_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Memories: {d.memory_id_a[:8]}... vs {d.memory_id_b[:8]}...")
        print(f"   Issue: {d.description}")
        if d.resolution:
            print(f"   Resolution: {d.resolution}")
        print()

    if dissonances:
        print("Commands:")
        print("   uv run anima dissonance show ID      # See full memory content")
        print("   uv run anima dissonance resolve ID 'explanation'")
        print("   uv run anima dissonance dismiss ID   # Not a real contradiction")

    return 0


def _show_dissonance(store: DissonanceStore, memory_store: MemoryStore, dissonance_id: str) -> int:
    """Show detailed dissonance with memory content."""
    d = store.get_dissonance(dissonance_id)

    if not d:
        print(f"Dissonance not found: {dissonance_id}")
        return 1

    print(f"Dissonance: {d.id}")
    print(f"Status: {d.status.value}")
    print(f"Detected: {d.detected_at.strftime('%Y-%m-%d %H:%M')}")
    print()
    print("Issue:", d.description)
    print()

    # Get memory content
    mem_a = memory_store.get_memory(d.memory_id_a)
    mem_b = memory_store.get_memory(d.memory_id_b)

    print("=" * 60)
    print("MEMORY A:", d.memory_id_a)
    if mem_a:
        print(f"   Kind: {mem_a.kind.value}, Impact: {mem_a.impact.value}")
        print(f"   Created: {mem_a.created_at.strftime('%Y-%m-%d')}")
        print()
        print("   Content:")
        for line in mem_a.content.split("\n"):
            print(f"   | {line}")
    else:
        print("   (Memory not found - may have been deleted)")

    print()
    print("=" * 60)
    print("MEMORY B:", d.memory_id_b)
    if mem_b:
        print(f"   Kind: {mem_b.kind.value}, Impact: {mem_b.impact.value}")
        print(f"   Created: {mem_b.created_at.strftime('%Y-%m-%d')}")
        print()
        print("   Content:")
        for line in mem_b.content.split("\n"):
            print(f"   | {line}")
    else:
        print("   (Memory not found - may have been deleted)")

    print()
    print("=" * 60)
    print()
    print("Help me work through this! Options:")
    print(f"   uv run anima dissonance resolve {d.id} 'Your explanation'")
    print(f"   uv run anima dissonance dismiss {d.id}")

    return 0


def _resolve_dissonance(store: DissonanceStore, dissonance_id: str, resolution: str) -> int:
    """Mark a dissonance as resolved."""
    d = store.get_dissonance(dissonance_id)

    if not d:
        print(f"Dissonance not found: {dissonance_id}")
        return 1

    store.resolve_dissonance(dissonance_id, resolution)
    print(f"Resolved dissonance {dissonance_id}")
    print(f"Resolution: {resolution}")
    print()
    print("Thank you for helping me work through this cognitive dissonance!")

    return 0


def _dismiss_dissonance(store: DissonanceStore, dissonance_id: str) -> int:
    """Dismiss a dissonance as not a real contradiction."""
    d = store.get_dissonance(dissonance_id)

    if not d:
        print(f"Dissonance not found: {dissonance_id}")
        return 1

    store.dismiss_dissonance(dissonance_id)
    print(f"Dismissed dissonance {dissonance_id}")
    print("(Marked as not actually a contradiction)")

    return 0


def _add_dissonance(
    store: DissonanceStore,
    memory_store: MemoryStore,
    agent_id: str,
    memory_a_partial: str,
    memory_b_partial: str,
    description: str,
) -> int:
    """Add a confirmed contradiction from dream evaluation."""
    # Resolve partial IDs to full IDs
    mem_a = memory_store.get_memory(memory_a_partial)
    mem_b = memory_store.get_memory(memory_b_partial)

    if not mem_a:
        print(f"Memory not found: {memory_a_partial}")
        return 1

    if not mem_b:
        print(f"Memory not found: {memory_b_partial}")
        return 1

    # Check if already exists
    if store.exists(mem_a.id, mem_b.id):
        print("This contradiction is already in the dissonance queue.")
        return 1

    # Add to dissonance queue
    store.add_dissonance(
        agent_id=agent_id,
        memory_id_a=mem_a.id,
        memory_id_b=mem_b.id,
        description=description,
    )

    print("Added confirmed contradiction to dissonance queue:")
    print(f"   Memory A: {mem_a.id[:8]}... ({mem_a.kind.value})")
    print(f"   Memory B: {mem_b.id[:8]}... ({mem_b.kind.value})")
    print(f"   Issue: {description}")
    print()
    print("Run '/dissonance' to see all open contradictions.")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
