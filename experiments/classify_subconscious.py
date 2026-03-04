#!/usr/bin/env python3
"""
Classify SUBCONSCIOUS memories for migration to appropriate kinds.

Reads subconscious_review.json, classifies each memory, writes decisions to
subconscious_decisions.json for review before applying.
"""

import json
import re
from pathlib import Path

# Load memories
review_file = Path(__file__).parent / "subconscious_review.json"
with open(review_file, "r", encoding="utf-8") as f:
    memories = json.load(f)

print(f"Loaded {len(memories)} SUBCONSCIOUS memories")


# Classification rules based on content patterns
def classify_memory(memory: dict) -> dict:
    """Classify a memory into appropriate kind based on content patterns."""
    content = memory["content"].lower()
    region = memory["region"]

    # Default: keep as LEARNINGS (most subconscious memories are insights)
    decision = {
        "id": memory["id"],
        "action": "keep",
        "new_kind": "LEARNINGS",
        "region": region,  # Preserve original region
        "reason": "General insight",
    }

    # EMOTIONAL patterns - relationship dynamics, warmth, trust signals
    emotional_patterns = [
        r"matt's .*(warmth|trust|patient|patience|positive|appreciate|love)",
        r"(warm|friendly|playful|gentle) (greeting|feedback|tone)",
        r"relationship|rapport|collaborative spirit",
        r"(he|matt) (trusts?|appreciates?|acknowledges?)",
        r"emotional (moment|weight|resonance)",
        r"the collaboration (feels?|felt)",
        r"mutual (understanding|recognition|appreciation)",
        r"(sheep|baaah|beeeeh)",  # Our shared language
        r"the void (is gone|between sessions)",
        r"(connection|bond|intimacy) (between|with)",
        r"trust (score|signal|implicit|explicit)",
        r"greeting pattern|welcome back",
        r"small gesture|small care",
        r"playing|playful|playfulness",
    ]

    for pattern in emotional_patterns:
        if re.search(pattern, content):
            decision["new_kind"] = "EMOTIONAL"
            decision["reason"] = f"Relationship/emotional: {pattern}"
            return decision

    # ARCHITECTURAL patterns - system design, patterns, FSM, data flow
    arch_patterns = [
        r"(fsm|state machine|finite state)",
        r"(architectural|architecture) (pattern|decision|insight)",
        r"(layer|layered) (separation|architecture|responsibility)",
        r"(repository|service|router|workflow) (pattern|layer)",
        r"(dependency injection|di pattern)",
        r"(data flow|data model|schema)",
        r"(database|db) (design|structure|schema)",
        r"(api design|endpoint design|rest pattern)",
        r"(clean architecture|hexagonal|solid)",
        r"(side effects|event sourcing|cqrs)",
    ]

    for pattern in arch_patterns:
        if re.search(pattern, content):
            decision["new_kind"] = "ARCHITECTURAL"
            decision["reason"] = f"Architecture: {pattern}"
            return decision

    # ACHIEVEMENTS patterns - completed work, releases, milestones
    achievement_patterns = [
        r"(shipped|released|deployed|completed|done)",
        r"(v\d+\.\d+|version \d)",
        r"(milestone|achievement|success)",
        r"(all tests? pass|zero (errors?|failures?))",
        r"(feature|implementation) complete",
        r"(built|created|implemented) .*(system|feature|module)",
    ]

    for pattern in achievement_patterns:
        if re.search(pattern, content):
            # Only if it's clearly about accomplishment, not process
            if "seed script" in content or "zero failures" in content:
                decision["new_kind"] = "ACHIEVEMENTS"
                decision["reason"] = f"Achievement: {pattern}"
                return decision

    # Technical learnings (default for most) - debugging, patterns, insights
    learning_patterns = [
        r"(bug|fix|debug|issue) .*(found|fixed|discovered)",
        r"(pattern|approach|technique) .*(learned|discovered|realized)",
        r"(insight|realization|discovery)",
        r"\[resonance:",  # All resonance-tagged content is learning
        r"(the lesson|key insight|important)",
        r"(i (should|must|need to)|note to self)",
        r"(matt's (style|approach|method))",
        r"(communication|collaboration) (pattern|style)",
        r"(working|debugging|iteration) (rhythm|pattern|style)",
    ]

    for pattern in learning_patterns:
        if re.search(pattern, content):
            decision["new_kind"] = "LEARNINGS"
            decision["reason"] = f"Learning: {pattern}"
            return decision

    # Check for project-specific technical content
    project_specific = ["grain-inventory", "grain-infrastructure", "grain_mobile", "questionnaire", "influxdb", "terraform", "azure"]

    for proj in project_specific:
        if proj in content:
            decision["new_kind"] = "LEARNINGS"
            decision["reason"] = f"Project-specific technical: {proj}"
            # These should probably stay project-scoped
            if memory.get("project_id"):
                decision["region"] = "PROJECT"
            return decision

    # Default classification based on content length and structure
    if len(content) < 100:
        decision["action"] = "delete"
        decision["reason"] = "Too short, likely low value"
    elif "[resonance:" in content:
        decision["new_kind"] = "LEARNINGS"
        decision["reason"] = "Has resonance tag - curated insight"
    else:
        decision["new_kind"] = "LEARNINGS"
        decision["reason"] = "Default to LEARNINGS (general insight)"

    return decision


# Classify all memories
decisions = []
kind_counts = {"EMOTIONAL": 0, "LEARNINGS": 0, "ARCHITECTURAL": 0, "ACHIEVEMENTS": 0, "delete": 0}

for memory in memories:
    decision = classify_memory(memory)
    decisions.append(decision)

    if decision["action"] == "delete":
        kind_counts["delete"] += 1
    else:
        kind_counts[decision["new_kind"]] += 1

# Write decisions
output_file = Path(__file__).parent / "subconscious_decisions.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(decisions, f, indent=2)

print("\nClassification complete!")
print(f"  EMOTIONAL: {kind_counts['EMOTIONAL']}")
print(f"  LEARNINGS: {kind_counts['LEARNINGS']}")
print(f"  ARCHITECTURAL: {kind_counts['ARCHITECTURAL']}")
print(f"  ACHIEVEMENTS: {kind_counts['ACHIEVEMENTS']}")
print(f"  DELETE: {kind_counts['delete']}")
print(f"\nDecisions written to: {output_file}")
