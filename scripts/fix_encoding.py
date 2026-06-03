#!/usr/bin/env python3
"""
Fix Windows encoding issues by adding explicit UTF-8 encoding to all file operations.

On Windows, Python defaults to the system locale encoding (e.g., cp1252) which
cannot decode UTF-8 multi-byte sequences. This script fixes all file read/write
operations to use explicit UTF-8 encoding.

Usage:
    python scripts/fix_encoding.py [--dry-run]
"""

import re
import sys
from pathlib import Path

# Files to exclude (already have proper encoding or are binary)
EXCLUDE_PATTERNS = [
    '*.pyc',
    '__pycache__',
    '.venv',
    '.git',
    'node_modules',
]


def should_exclude(path: Path) -> bool:
    """Check if path should be excluded."""
    path_str = str(path)
    for pattern in EXCLUDE_PATTERNS:
        if pattern in path_str:
            return True
    return False


def fix_line(line: str) -> str:
    """Fix encoding issues in a single line."""
    # Skip if already has encoding
    if 'encoding=' in line or 'encoding =' in line:
        return line

    # Skip comments
    stripped = line.lstrip()
    if stripped.startswith('#'):
        return line

    # Skip method/function definitions (def open, def read_text, etc.)
    if re.match(r'\s*def\s+\w+', line):
        return line

    # Fix: .read_text() -> .read_text(encoding="utf-8")
    line = re.sub(
        r'\.read_text\(\s*\)',
        '.read_text(encoding="utf-8")',
        line
    )

    # Fix: .write_text(content) -> .write_text(content, encoding="utf-8")
    # Match .write_text(...) but not if encoding already present
    # This handles both simple and complex arguments including json.dumps()
    def fix_write_text(m):
        full_match = m.group(0)
        if 'encoding' in full_match:
            return full_match
        # Find the last ) that closes write_text
        # We need to handle nested parens like .write_text(json.dumps(data))
        content = m.group(1)
        return f'.write_text({content}, encoding="utf-8")'

    # Use a more careful regex that handles nested parentheses
    # Match .write_text( then capture everything up to the matching )
    if '.write_text(' in line and 'encoding' not in line:
        # Find .write_text( position
        idx = line.find('.write_text(')
        if idx != -1:
            start = idx + len('.write_text(')
            # Count parens to find matching close
            depth = 1
            end = start
            while end < len(line) and depth > 0:
                if line[end] == '(':
                    depth += 1
                elif line[end] == ')':
                    depth -= 1
                end += 1
            if depth == 0:
                # end points to just after the closing )
                content = line[start:end-1]
                line = line[:start] + content + ', encoding="utf-8")' + line[end:]

    # Fix: with open(path) as f -> with open(path, encoding="utf-8") as f
    # But NOT 'def open' or other non-file-open uses
    # Match: open(path) followed by 'as' (context manager)
    line = re.sub(
        r'\bopen\(([^,\)]+)\)\s+as\b',
        r'open(\1, encoding="utf-8") as',
        line
    )

    # Fix: with open(path, "r") as f -> with open(path, "r", encoding="utf-8") as f
    # Match: open(path, mode) followed by 'as'
    line = re.sub(
        r'\bopen\(([^,\)]+),\s*(["\'][rwa]["\'])\)\s+as\b',
        r'open(\1, \2, encoding="utf-8") as',
        line
    )

    return line


def fix_file(filepath: Path, dry_run: bool = False) -> list[tuple[int, str, str]]:
    """
    Fix encoding issues in a single file.

    Returns list of (line_number, old_line, new_line) tuples for changes made.
    """
    changes = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  WARNING: Could not read {filepath} (encoding error)")
        return changes

    lines = content.split('\n')
    new_lines = []

    for i, line in enumerate(lines, 1):
        original_line = line
        line = fix_line(line)
        new_lines.append(line)

        if line != original_line:
            changes.append((i, original_line.strip(), line.strip()))

    if changes and not dry_run:
        new_content = '\n'.join(new_lines)
        filepath.write_text(new_content, encoding="utf-8")

    return changes


def main():
    dry_run = '--dry-run' in sys.argv

    if dry_run:
        print("DRY RUN - no files will be modified\n")

    # Find all Python files in anima/
    anima_dir = Path(__file__).parent.parent / "anima"

    if not anima_dir.exists():
        print(f"ERROR: {anima_dir} not found")
        sys.exit(1)

    total_changes = 0
    files_changed = 0

    for py_file in sorted(anima_dir.rglob("*.py")):
        if should_exclude(py_file):
            continue

        changes = fix_file(py_file, dry_run)

        if changes:
            files_changed += 1
            total_changes += len(changes)
            rel_path = py_file.relative_to(anima_dir.parent)
            print(f"\n{rel_path}:")
            for line_num, old, new in changes:
                print(f"  L{line_num}:")
                print(f"    - {old}")
                print(f"    + {new}")

    print(f"\n{'Would change' if dry_run else 'Changed'} {total_changes} lines in {files_changed} files")

    if dry_run and total_changes > 0:
        print("\nRun without --dry-run to apply changes")


if __name__ == "__main__":
    main()
