# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Seed memory importer for LTM.

Imports seed memories from markdown files in gemini-docs/memories/
to bootstrap LTM with its founding memories.
"""

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from anima.core import Memory, MemoryKind, ImpactLevel, RegionType, AgentResolver
from anima.lifecycle.injection import ensure_token_count
from anima.storage import MemoryStore
from anima.utils.terminal import safe_print, get_icon


def parse_seed_file(file_path: Path) -> Optional[dict]:
    """
    Parse a seed memory file.

    Expected format:
    ```
    # Title

    **ID:** TYPE-YYYY-MM-DD-NNN
    **Created:** YYYY-MM-DD
    **Impact:** CRITICAL|HIGH|MEDIUM|LOW
    **Region:** AGENT|PROJECT (ProjectName)
    **Confidence:** 0.0-1.0

    ## Raw Memory (Original)
    ...content...

    ## Compacted Memory (For Injection)
    ```
    ~TYPE:IMPACT| content
    ```
    ```

    Returns dict with parsed fields or None if parsing fails.
    """
    content = file_path.read_text()

    result: dict = {
        "id": None,
        "created_at": None,
        "impact": None,
        "region": None,
        "project": None,
        "confidence": 1.0,
        "kind": None,
        "raw_content": None,
        "compacted_content": None,
    }

    # Parse header fields
    id_match = re.search(r"\*\*ID:\*\*\s*(\S+)", content)
    if id_match:
        result["id"] = id_match.group(1)
        # Infer kind from ID prefix
        id_prefix = result["id"].split("-")[0]
        kind_map = {
            "EMOT": MemoryKind.EMOTIONAL,
            "ARCH": MemoryKind.ARCHITECTURAL,
            "LEARN": MemoryKind.LEARNINGS,
            "ACHV": MemoryKind.ACHIEVEMENTS,
        }
        result["kind"] = kind_map.get(id_prefix, MemoryKind.LEARNINGS)

    created_match = re.search(r"\*\*Created:\*\*\s*(\d{4}-\d{2}-\d{2})", content)
    if created_match:
        result["created_at"] = datetime.strptime(created_match.group(1), "%Y-%m-%d")

    impact_match = re.search(r"\*\*Impact:\*\*\s*(CRITICAL|HIGH|MEDIUM|LOW)", content)
    if impact_match:
        result["impact"] = ImpactLevel(impact_match.group(1))

    region_match = re.search(r"\*\*Region:\*\*\s*(AGENT|PROJECT)(?:\s*\(([^)]+)\))?", content)
    if region_match:
        result["region"] = RegionType(region_match.group(1))
        if region_match.group(2):
            result["project"] = region_match.group(2)

    confidence_match = re.search(r"\*\*Confidence:\*\*\s*([\d.]+)", content)
    if confidence_match:
        result["confidence"] = float(confidence_match.group(1))

    # Parse raw content (between ## Raw Memory and ## Compacted Memory)
    raw_match = re.search(r"## Raw Memory.*?\n\n(.*?)(?=\n## Compacted Memory)", content, re.DOTALL)
    if raw_match:
        result["raw_content"] = raw_match.group(1).strip()

    # Parse compacted content (in code block after ## Compacted Memory)
    compacted_match = re.search(r"## Compacted Memory.*?```\n(.*?)\n```", content, re.DOTALL)
    if compacted_match:
        result["compacted_content"] = compacted_match.group(1).strip()

    # Validate required fields
    if not all(
        [
            result["id"],
            result["created_at"],
            result["impact"],
            result["region"],
            result["kind"],
            result["raw_content"],
        ]
    ):
        return None

    return result


def run(args: list[str]) -> int:
    """
    Run the seed importer.

    Args:
        args: Path to directory containing seed files

    Returns:
        Exit code (0 for success)
    """
    if not args:
        print("Usage: uv run anima import-seeds <directory>")
        print("Example: uv run anima import-seeds gemini-docs/memories/")
        return 1

    seed_dir = Path(args[0])
    if not seed_dir.exists():
        print(f"Directory not found: {seed_dir}")
        return 1

    # Find all seed files
    seed_files = list(seed_dir.glob("*.md"))
    seed_files = [f for f in seed_files if f.name != "README.md"]

    if not seed_files:
        print(f"No seed files found in {seed_dir}")
        return 1

    print(f"Found {len(seed_files)} seed files in {seed_dir}\n")

    # Initialize store
    store = MemoryStore()

    # Resolve agent and project from config (same as SessionStart)
    resolver = AgentResolver(Path.cwd())
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store.save_agent(agent)
    store.save_project(project)

    print(f"Importing seeds for agent: {agent.name} ({agent.id})")

    imported = 0
    skipped = 0

    for seed_file in sorted(seed_files):
        print(f"Processing: {seed_file.name}")

        parsed = parse_seed_file(seed_file)
        if not parsed:
            safe_print(f"  {get_icon('⚠️', '[!]')}  Failed to parse, skipping")
            skipped += 1
            continue

        # Check if already imported (by ID)
        existing = store.get_memory(parsed["id"])
        if existing:
            safe_print(f"  {get_icon('⏭️', '[>>]')}  Already imported, skipping")
            skipped += 1
            continue

        # Use compacted content if available, otherwise raw
        content = parsed["compacted_content"] or parsed["raw_content"]

        # Strip DSL prefix if present (seed files may already have it)
        # e.g., "~ARCH:CRIT| content" -> "content"
        if content.startswith("~"):
            # Remove all DSL prefixes (there might be multiple lines)
            lines = content.split("\n")
            cleaned_lines = []
            for line in lines:
                if line.startswith("~") and "|" in line:
                    # Strip the prefix up to and including the first |
                    line = line.split("|", 1)[1].strip()
                cleaned_lines.append(line)
            content = "\n".join(cleaned_lines)

        # Create memory
        memory = Memory(
            id=parsed["id"],  # Preserve original ID
            agent_id=agent.id,
            region=parsed["region"],
            project_id=project.id if parsed["region"] == RegionType.PROJECT else None,
            kind=parsed["kind"],
            content=content,
            original_content=parsed["raw_content"],
            impact=parsed["impact"],
            confidence=parsed["confidence"],
            created_at=parsed["created_at"],
            last_accessed=parsed["created_at"],  # Preserve original timestamp
        )

        ensure_token_count(memory)
        store.save_memory(memory)
        imported += 1

        safe_print(f"  {get_icon('✅', '[OK]')} Imported: {parsed['kind'].value} ({parsed['impact'].value})")

    print(f"\nImport complete: {imported} imported, {skipped} skipped")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
