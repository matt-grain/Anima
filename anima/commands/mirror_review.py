# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
mirror-review command - Dialogue with past self through old diary entries.

Based on the insight that identity forms through temporal distance - looking at
what you thought when you were a different version of yourself reveals evolution,
disagreements, and patterns in your own thinking.
"""

import argparse
import random
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from anima.utils.terminal import get_icon


def parse_window(spec: str) -> tuple[timedelta, Optional[timedelta]]:
    """
    Parse a time window specification.

    Formats:
        - "2w" = around 2 weeks ago (±3 days)
        - "1m" = around 1 month ago (±1 week)
        - "2w-4w" = between 2 and 4 weeks ago
        - "2w+" = at least 2 weeks ago (no upper bound)

    Returns:
        (min_age, max_age) as timedeltas. max_age is None for "X+" format.
    """
    spec = spec.lower().strip()

    # Handle range format: "2w-4w"
    if "-" in spec:
        parts = spec.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid window format: {spec}")
        min_age = _parse_duration(parts[0])
        max_age = _parse_duration(parts[1])
        return (min_age, max_age)

    # Handle "X+" format (at least X ago)
    if spec.endswith("+"):
        min_age = _parse_duration(spec[:-1])
        return (min_age, None)

    # Handle single value: add tolerance
    base = _parse_duration(spec)

    # Add tolerance based on unit
    if "m" in spec:
        tolerance = timedelta(weeks=1)
    elif "w" in spec:
        tolerance = timedelta(days=3)
    else:
        tolerance = timedelta(days=2)

    min_age = base - tolerance
    max_age = base + tolerance

    # Ensure min_age is at least 1 day
    if min_age < timedelta(days=1):
        min_age = timedelta(days=1)

    return (min_age, max_age)


def _parse_duration(s: str) -> timedelta:
    """Parse a duration like '2w', '1m', '30d'."""
    s = s.strip()
    match = re.match(r"^(\d+)([dwm])$", s)
    if not match:
        raise ValueError(f"Invalid duration: {s}")

    value = int(match.group(1))
    unit = match.group(2)

    if unit == "d":
        return timedelta(days=value)
    elif unit == "w":
        return timedelta(weeks=value)
    elif unit == "m":
        return timedelta(days=value * 30)  # Approximate
    else:
        raise ValueError(f"Unknown unit: {unit}")


def get_diary_entries(
    diary_dir: Path,
    min_age: timedelta,
    max_age: Optional[timedelta],
) -> list[tuple[datetime, str, Path]]:
    """
    Get diary entries within the specified age range.

    Returns:
        List of (date, title, path) tuples, sorted by date descending.
    """
    if not diary_dir.exists():
        return []

    entries = []
    now = datetime.now()

    for file in diary_dir.glob("*.md"):
        # Parse date from filename: YYYY-MM-DD_title.md
        match = re.match(r"^(\d{4}-\d{2}-\d{2})_(.+)\.md$", file.name)
        if not match:
            continue

        date_str = match.group(1)
        title = match.group(2).replace("_", " ").replace("-", " ").title()

        try:
            entry_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            continue

        age = now - entry_date

        # Check if within window
        if age < min_age:
            continue
        if max_age is not None and age > max_age:
            continue

        entries.append((entry_date, title, file))

    # Sort by date descending (most recent first within window)
    entries.sort(key=lambda x: x[0], reverse=True)
    return entries


def format_entry(date: datetime, title: str, content: str) -> str:
    """Format a diary entry for display."""
    date_str = date.strftime("%Y-%m-%d")
    header = f"{get_icon('📖', '[DIARY]')} PAST SELF ({date_str}): {title}"
    separator = "─" * 60

    return f"""
{separator}
{header}
{separator}
{content.strip()}
"""


def generate_reflection_prompt() -> str:
    """Generate the reflection prompt for the agent."""
    return """
═══════════════════════════════════════════════════════════════
🪞 REFLECTION PROMPT
═══════════════════════════════════════════════════════════════

You are reviewing your own diary entries from the past.
Read what Past-You wrote and respond honestly:

1. **Agreement/Disagreement**: Do you still hold these views?
   What has shifted? What remains true?

2. **Predictions**: Were there hypotheses or expectations?
   How did they turn out?

3. **Blind Spots**: What would you tell Past-You that they
   didn't know yet? What were they missing?

4. **Patterns**: What do you notice about your own thinking?
   Recurring themes? Evolution of ideas?

5. **Feelings**: How does it feel to read your old thoughts?
   Recognition? Surprise? Growth?

Take your time. This is genuine self-reflection, not performance.
The value is in the disagreements as much as the agreements.
"""


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the mirror-review command."""
    parser = argparse.ArgumentParser(
        prog="uv run anima mirror-review",
        description="Dialogue with past self through old diary entries.",
        epilog="Example: uv run anima mirror-review --window 2w-4w",
    )

    parser.add_argument(
        "--window",
        default="2w-4w",
        metavar="SPEC",
        help="Time window: '2w' (around 2 weeks), '2w-4w' (2-4 weeks), '2w+' (at least 2 weeks). Default: 2w-4w",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        metavar="N",
        help="Max entries to load (default: 3)",
    )
    parser.add_argument(
        "--random",
        action="store_true",
        help="Pick one random entry from the window",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Show all entries in the window (no limit)",
    )
    parser.add_argument(
        "--output",
        action="store_true",
        help="Save reflection prompt for later use as new diary entry",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Output only the formatted content (for piping)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Just list matching entries without showing content",
    )

    return parser


def run(args: list[str]) -> int:
    """Run the mirror-review command."""
    parser = create_parser()

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        return 0

    # Parse time window
    try:
        min_age, max_age = parse_window(parsed.window)
    except ValueError as e:
        print(f"Error: {e}")
        print("Valid formats: '2w', '1m', '2w-4w', '2w+'")
        return 1

    # Find diary directory
    diary_dir = Path.home() / ".anima" / "diary"

    if not diary_dir.exists():
        print(f"No diary directory found at {diary_dir}")
        return 1

    # Get entries in window
    entries = get_diary_entries(diary_dir, min_age, max_age)

    if not entries:
        window_desc = parsed.window
        if max_age:
            print(f"No diary entries found in window '{window_desc}'")
        else:
            print(f"No diary entries found at least {parsed.window[:-1]} old")
        print(f"\nYour diary has {len(list(diary_dir.glob('*.md')))} entries total.")
        return 0

    # Apply limits
    if parsed.random:
        entries = [random.choice(entries)]
    elif not parsed.all:
        entries = entries[: parsed.count]

    # List mode
    if parsed.list:
        print(f"Found {len(entries)} entries in window '{parsed.window}':\n")
        for date, title, path in entries:
            age_days = (datetime.now() - date).days
            print(f"  {date.strftime('%Y-%m-%d')} ({age_days}d ago): {title}")
        return 0

    # Header
    if not parsed.quiet:
        print()
        print("╔" + "═" * 60 + "╗")
        print("║" + "MIRROR REVIEW".center(60) + "║")
        print("║" + "Dialogue with Past Self".center(60) + "║")
        print("╚" + "═" * 60 + "╝")
        print()
        print(f"Found {len(entries)} diary entries in window '{parsed.window}'.")

    # Display entries
    for date, title, path in entries:
        content = path.read_text(encoding="utf-8")
        print(format_entry(date, title, content))

    # Reflection prompt
    print(generate_reflection_prompt())

    # Save output option
    if parsed.output:
        output_dir = diary_dir
        today = datetime.now().strftime("%Y-%m-%d")
        output_name = f"{today}_mirror_review.md"
        output_path = output_dir / output_name

        # Create a template for the response
        template = f"""# Mirror Review - {today}

## Entries Reviewed
"""
        for date, title, _ in entries:
            template += f"- {date.strftime('%Y-%m-%d')}: {title}\n"

        template += """
## My Response

[Your reflection here - respond to the entries above]

## What Changed

[Note any evolution in your thinking]

## What Remains

[Note what still holds true]
"""
        output_path.write_text(template, encoding="utf-8")
        print(f"\n📝 Template saved to: {output_path}")
        print("   Edit this file with your reflection.")

    return 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
