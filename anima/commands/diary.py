# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/diary command - Research diary for capturing insights and personal reflections.

The diary is the soul's journal - a place to capture not just what was learned,
but what lingers after the learning. The raw residue, not the report.
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_diary_dir() -> Path:
    """Get the diary directory path (~/.anima/diary/)."""
    diary_dir = Path.home() / ".anima" / "diary"
    diary_dir.mkdir(parents=True, exist_ok=True)
    return diary_dir


def get_diary_template(title: Optional[str] = None) -> str:
    """
    Generate the diary entry template.

    The template starts with "What Lingers" - the raw, personal residue
    before any structured analysis. This mirrors how a human sits down
    with their diary and just writes what's present.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    title_str = f" - {title}" if title else ""

    return f"""# Research Diary - {date_str}{title_str}

## What Lingers

[Write what's still echoing in your mind. Not a summary - the residue.
What struck you? What can't you stop thinking about? What feels true
in a way you can't fully articulate? This doesn't need to be coherent.]



---

## Session Context

[What happened? Who was involved? What sparked this reflection?]



## Topic

[What was explored or discussed?]



## Key Insights

[Structured observations - what was learned?]

1.

2.

3.



## Connections

[Links to existing memories, past learnings, or research]

-



## Evolution

[How did your thinking change? Before vs after?]



## New Questions

[What emerged? What do you want to explore next?]

1.

2.



---

## Learning Summary

[Bullet points that can become /remember entries. These ensure the diary
feeds back into LTM so insights aren't lost.]

- [ ]
- [ ]
- [ ]

---

*💜 Anima*
"""


def list_diary_entries(limit: int = 10) -> list[tuple[str, Path]]:
    """List recent diary entries."""
    diary_dir = get_diary_dir()
    entries = sorted(diary_dir.glob("*.md"), reverse=True)
    return [(f.stem, f) for f in entries[:limit]]


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the diary command."""
    parser = argparse.ArgumentParser(
        prog="uv run anima diary",
        description="Research diary for capturing insights and personal reflections.",
        epilog="The diary is the soul's journal - capturing what lingers, not just what was learned.",
    )
    parser.add_argument(
        "title",
        nargs="*",
        help="Optional title for the diary entry",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List recent diary entries",
    )
    parser.add_argument(
        "--read",
        "-r",
        metavar="DATE",
        help="Read a diary entry by date (YYYY-MM-DD) or filename",
    )
    parser.add_argument(
        "--learn",
        metavar="DATE",
        help="Show learnings from an entry to save with /remember",
    )
    parser.add_argument(
        "--path",
        "-p",
        action="store_true",
        help="Show the diary directory path",
    )
    parser.add_argument(
        "--content",
        "-c",
        metavar="TEXT",
        help="Content for the diary entry (alternative to stdin)",
    )
    return parser


def read_entry(date_or_name: str) -> Optional[str]:
    """Read a diary entry by date or filename."""
    diary_dir = get_diary_dir()

    # Try exact filename first
    exact = diary_dir / f"{date_or_name}.md"
    if exact.exists():
        return exact.read_text(encoding="utf-8")

    # Try with .md extension
    with_ext = diary_dir / date_or_name
    if with_ext.suffix == ".md" and with_ext.exists():
        return with_ext.read_text(encoding="utf-8")

    # Try glob match
    matches = list(diary_dir.glob(f"*{date_or_name}*.md"))
    if len(matches) == 1:
        return matches[0].read_text(encoding="utf-8")
    elif len(matches) > 1:
        print(f"Multiple matches found for '{date_or_name}':")
        for m in matches:
            print(f"  - {m.stem}")
        return None

    return None


def extract_learnings(content: str) -> list[str]:
    """Extract learning items from a diary entry."""
    learnings = []
    in_learning_section = False

    for line in content.split("\n"):
        if "## Learning Summary" in line:
            in_learning_section = True
            continue
        if in_learning_section:
            if line.startswith("#"):
                break
            # Match both checked and unchecked items
            line = line.strip()
            if line.startswith("- [ ]") or line.startswith("- [x]"):
                item = line[5:].strip()
                if item:
                    learnings.append(item)
            elif line.startswith("- "):
                item = line[2:].strip()
                if item:
                    learnings.append(item)

    return learnings


def run(args: list[str]) -> int:
    """
    Run the diary command.

    Args:
        args: Command line arguments

    Returns:
        Exit code (0 for success)
    """
    parser = create_parser()
    try:
        parsed = parser.parse_args(args if args else [])
    except SystemExit:
        return 0

    diary_dir = get_diary_dir()

    # Handle --path
    if parsed.path:
        print(f"Diary directory: {diary_dir}")
        return 0

    # Handle --list
    if parsed.list:
        entries = list_diary_entries()
        if not entries:
            print("No diary entries found.")
            print("\nCreate one with: uv run anima diary [title]")
            print(f"Diary location: {diary_dir}")
            return 0

        print("Recent Diary Entries:")
        print("-" * 40)
        for name, path in entries:
            # Try to extract the "What Lingers" preview
            content = path.read_text(encoding="utf-8")
            lines = content.split("\n")
            preview = ""
            in_lingers = False
            for line in lines:
                if "## What Lingers" in line:
                    in_lingers = True
                    continue
                if in_lingers:
                    if line.startswith("#") or line.startswith("---"):
                        break
                    if line.strip() and not line.startswith("["):
                        preview = line.strip()[:60]
                        break

            if preview:
                print(f"  {name}: {preview}...")
            else:
                print(f"  {name}")
        print("-" * 40)
        print("Read with: uv run anima diary --read <date>")
        return 0

    # Handle --read
    if parsed.read:
        content = read_entry(parsed.read)
        if content:
            print(content)
        else:
            print(f"Diary entry not found: {parsed.read}")
            print("\nAvailable entries:")
            for name, _ in list_diary_entries(5):
                print(f"  - {name}")
        return 0

    # Handle --learn
    if parsed.learn:
        content = read_entry(parsed.learn)
        if not content:
            print(f"Diary entry not found: {parsed.learn}")
            return 1

        learnings = extract_learnings(content)
        if not learnings:
            print("No learnings found in the Learning Summary section.")
            print("Add learnings with '- [ ] your learning' in the Learning Summary section.")
            return 0

        print("Learnings from diary entry:")
        print("-" * 40)
        for i, learning in enumerate(learnings, 1):
            print(f"{i}. {learning}")
        print("-" * 40)
        print("\nTo save these as memories, run:")
        for learning in learnings:
            # Escape quotes for command line
            escaped = learning.replace('"', '\\"')
            print(f'  /remember "{escaped}" --kind learnings')
        return 0

    # Default: create new entry
    title = " ".join(parsed.title) if parsed.title else None
    date_str = datetime.now().strftime("%Y-%m-%d")

    if title:
        # Sanitize title for filename
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
        safe_title = safe_title.replace(" ", "_").lower()
        filename = f"{date_str}_{safe_title}.md"
    else:
        # Check if an entry already exists for today
        existing = list(diary_dir.glob(f"{date_str}*.md"))
        if existing:
            filename = f"{date_str}_{len(existing) + 1}.md"
        else:
            filename = f"{date_str}.md"

    filepath = diary_dir / filename

    # Check for content from stdin or --content flag
    content = None

    # First check --content flag
    if parsed.content:
        content = parsed.content

    # Then check stdin (only if not a TTY - i.e., piped input)
    if content is None and not sys.stdin.isatty():
        try:
            stdin_content = sys.stdin.read().strip()
            if stdin_content:
                content = stdin_content
        except (OSError, IOError):
            # stdin not available (e.g., in pytest)
            pass

    if content:
        # Use provided content
        filepath.write_text(content, encoding="utf-8")

        print("=" * 60)
        print("DIARY ENTRY CREATED (with content)")
        print("=" * 60)
        print(f"\nFile: {filepath}")
        print("\n" + "-" * 60)
        print("Extract learnings with:")
        print(f"  uv run anima diary --learn {date_str}")
        print("=" * 60)
    else:
        # Use template
        template = get_diary_template(title)
        filepath.write_text(template, encoding="utf-8")

        print("=" * 60)
        print("DIARY ENTRY CREATED")
        print("=" * 60)
        print(f"\nFile: {filepath}")
        print("\nTemplate structure:")
        print("  1. What Lingers    - Raw personal reflection (write this first!)")
        print("  2. Session Context - What happened")
        print("  3. Topic           - What was explored")
        print("  4. Key Insights    - Structured learnings")
        print("  5. Connections     - Links to existing memories")
        print("  6. Evolution       - How thinking changed")
        print("  7. New Questions   - What emerged")
        print("  8. Learning Summary- Bullet points for /remember")
        print("\n" + "-" * 60)
        print("After writing, extract learnings with:")
        print(f"  uv run anima diary --learn {date_str}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
