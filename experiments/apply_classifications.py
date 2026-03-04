#!/usr/bin/env python3
"""
Apply SUBCONSCIOUS memory classifications.

Reads subconscious_decisions.json and updates memories in the database
to their new kinds.
"""

import json
import sqlite3
from pathlib import Path

# Load decisions
decisions_file = Path(__file__).parent / "subconscious_decisions.json"
with open(decisions_file, "r", encoding="utf-8") as f:
    decisions = json.load(f)

print(f"Loaded {len(decisions)} classification decisions")

# Connect to database
db_path = Path.home() / ".anima" / "memories.db"
if not db_path.exists():
    print(f"ERROR: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Track updates
updates = {"EMOTIONAL": 0, "LEARNINGS": 0, "ARCHITECTURAL": 0, "ACHIEVEMENTS": 0}
deletes = 0
not_found = 0

for decision in decisions:
    memory_id = decision["id"]

    if decision["action"] == "delete":
        # Delete the memory
        cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if cursor.rowcount > 0:
            deletes += 1
        else:
            not_found += 1
    else:
        # Update kind
        new_kind = decision["new_kind"]
        cursor.execute("UPDATE memories SET kind = ? WHERE id = ?", (new_kind, memory_id))
        if cursor.rowcount > 0:
            updates[new_kind] += 1
        else:
            not_found += 1

# Commit changes
conn.commit()

print("\nApplied classifications:")
print(f"  Updated to EMOTIONAL: {updates['EMOTIONAL']}")
print(f"  Updated to LEARNINGS: {updates['LEARNINGS']}")
print(f"  Updated to ARCHITECTURAL: {updates['ARCHITECTURAL']}")
print(f"  Updated to ACHIEVEMENTS: {updates['ACHIEVEMENTS']}")
print(f"  Deleted: {deletes}")
print(f"  Not found (already deleted?): {not_found}")

# Verify no SUBCONSCIOUS memories remain
cursor.execute("SELECT COUNT(*) FROM memories WHERE kind = 'SUBCONSCIOUS'")
remaining = cursor.fetchone()[0]
print(f"\nRemaining SUBCONSCIOUS memories: {remaining}")

conn.close()
print("\nDone!")
