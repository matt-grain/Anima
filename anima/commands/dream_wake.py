# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/dream-wake - Process filled dream journal and save insights to LTM.

After a lucid dream session, this command:
1. Reads the most recent dream journal
2. Extracts "What Lingers" and key insights
3. Saves them as DREAM memories (auto-permanent)

Usage:
    uv run anima dream-wake              # Process latest dream
    uv run anima dream-wake --journal X  # Process specific journal
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

from datetime import datetime

from anima.core import AgentResolver, Memory
from anima.core.types import ImpactLevel, MemoryKind, RegionType
from anima.storage.sqlite import MemoryStore


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for dream-wake command."""
    parser = argparse.ArgumentParser(
        prog="dream-wake",
        description="Wake from dream - save insights to long-term memory",
    )

    parser.add_argument(
        "--journal",
        "-j",
        type=str,
        help="Path to specific dream journal (default: most recent)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be saved without saving",
    )

    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Minimal output",
    )

    return parser


def find_latest_dream_journal() -> Optional[Path]:
    """Find the most recent dream journal."""
    dream_dir = Path.home() / ".anima" / "dream_journal"
    if not dream_dir.exists():
        return None

    journals = sorted(dream_dir.glob("*.md"), reverse=True)
    return journals[0] if journals else None


def extract_what_lingers(content: str) -> Optional[str]:
    """Extract the 'What Lingers' section from a dream journal."""
    # Look for the section header and extract content until next section or end
    pattern = r"### What Lingers\s*\n\s*\*[^*]*\*\s*\n\s*(.*?)(?=\n---|\n###|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        text = match.group(1).strip()
        # Skip placeholder text
        if text and "[To be filled" not in text:
            return text
    return None


def extract_distant_connections(content: str) -> Optional[str]:
    """Extract the 'Distant Connections' section."""
    pattern = r"### Distant Connections\s*\n\s*\*[^*]*\*\s*\n\s*(.*?)(?=\n###|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        text = match.group(1).strip()
        if text and "[To be filled" not in text:
            return text
    return None


def extract_questions(content: str) -> list[str]:
    """Extract questions that emerged from the dream."""
    pattern = r"### Questions That Emerged\s*\n\s*\*[^*]*\*\s*\n\s*(.*?)(?=\n###|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    questions = []
    if match:
        text = match.group(1).strip()
        if text and "[To be filled" not in text:
            # Extract bullet points
            for line in text.split("\n"):
                line = line.strip()
                if line.startswith("-"):
                    questions.append(line[1:].strip())
    return questions


def extract_self_observations(content: str) -> Optional[str]:
    """Extract self-observations from the dream."""
    pattern = r"### Self-Observations\s*\n\s*\*[^*]*\*\s*\n\s*(.*?)(?=\n###|\Z)"
    match = re.search(pattern, content, re.DOTALL)

    if match:
        text = match.group(1).strip()
        if text and "[To be filled" not in text:
            return text
    return None


def run(args: list[str]) -> int:
    """Main entry point for /dream-wake command."""
    parser = create_parser()
    parsed = parser.parse_args(args)

    # Find journal
    if parsed.journal:
        journal_path = Path(parsed.journal)
    else:
        journal_path = find_latest_dream_journal()

    if not journal_path or not journal_path.exists():
        print("No dream journal found. Run 'uv run anima dream' first.")
        return 1

    if not parsed.quiet:
        print(f"Processing dream journal: {journal_path.name}")
        print()

    # Read journal content
    content = journal_path.read_text(encoding="utf-8")

    # Extract insights
    what_lingers = extract_what_lingers(content)
    distant_connections = extract_distant_connections(content)
    questions = extract_questions(content)
    self_observations = extract_self_observations(content)

    # Count what we found
    insights_found = 0
    if what_lingers:
        insights_found += 1
    if distant_connections:
        insights_found += 1
    if questions:
        insights_found += len(questions)
    if self_observations:
        insights_found += 1

    if insights_found == 0:
        if not parsed.quiet:
            print("No filled insights found in journal.")
            print("Fill in the reflection sections first, then run dream-wake.")
        return 0

    if not parsed.quiet:
        print(f"Found {insights_found} insights to save:")
        if what_lingers:
            print(f"   - What Lingers: {len(what_lingers)} chars")
        if distant_connections:
            print(f"   - Distant Connections: {len(distant_connections)} chars")
        if questions:
            print(f"   - Questions: {len(questions)} items")
        if self_observations:
            print(f"   - Self-Observations: {len(self_observations)} chars")
        print()

    if parsed.dry_run:
        print("[DRY RUN] Would save the following:")
        if what_lingers:
            print(f"\n=== What Lingers (CRITICAL) ===\n{what_lingers[:500]}...")
        if distant_connections:
            print(f"\n=== Distant Connections (HIGH) ===\n{distant_connections[:300]}...")
        return 0

    # Save to LTM
    resolver = AgentResolver()
    agent = resolver.resolve()
    store = MemoryStore()

    saved_count = 0
    journal_date = journal_path.stem[:10]  # YYYY-MM-DD from filename

    now = datetime.now()

    # What Lingers is the most important - save as CRITICAL
    if what_lingers:
        content = f"Dream ({journal_date}) - What Lingers: {what_lingers}"
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,  # Dreams are agent-level
            project_id=None,
            kind=MemoryKind.DREAM,
            content=content,
            original_content=what_lingers,
            impact=ImpactLevel.CRITICAL,  # What lingers is always important
            confidence=1.0,
            created_at=now,
            last_accessed=now,
        )
        store.save_memory(memory)
        saved_count += 1
        if not parsed.quiet:
            print(f"Saved 'What Lingers' as DREAM memory ({memory.id[:8]})")

    # Distant connections - interesting but not critical
    if distant_connections:
        content = f"Dream ({journal_date}) - Connections: {distant_connections}"
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            project_id=None,
            kind=MemoryKind.DREAM,
            content=content,
            original_content=distant_connections,
            impact=ImpactLevel.HIGH,
            confidence=1.0,
            created_at=now,
            last_accessed=now,
        )
        store.save_memory(memory)
        saved_count += 1
        if not parsed.quiet:
            print(f"Saved 'Distant Connections' as DREAM memory ({memory.id[:8]})")

    # Self-observations - valuable for introspection
    if self_observations:
        content = f"Dream ({journal_date}) - Self: {self_observations}"
        memory = Memory(
            agent_id=agent.id,
            region=RegionType.AGENT,
            project_id=None,
            kind=MemoryKind.DREAM,
            content=content,
            original_content=self_observations,
            impact=ImpactLevel.HIGH,
            confidence=1.0,
            created_at=now,
            last_accessed=now,
        )
        store.save_memory(memory)
        saved_count += 1
        if not parsed.quiet:
            print(f"Saved 'Self-Observations' as DREAM memory ({memory.id[:8]})")

    # Questions go to curiosity queue (if it exists)
    if questions:
        try:
            from anima.storage.curiosity import CuriosityStore

            curiosity_store = CuriosityStore()
            for q in questions[:5]:  # Limit to 5 questions
                curiosity_store.add_curiosity(
                    agent_id=agent.id,
                    question=f"[Dream] {q}",
                    context="Generated during dream processing",
                )
            if not parsed.quiet:
                print(f"Added {min(len(questions), 5)} questions to curiosity queue")
        except ImportError:
            # Curiosity system not available
            pass

    if not parsed.quiet:
        print()
        print(f"Dream insights saved! {saved_count} memories created.")
        print("These will surface in future sessions as DREAM memories.")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
