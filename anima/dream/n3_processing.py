# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
N3 - Deep Processing Stage

Character: Analytical, reductive, truth-seeking. The editor cutting to essence.

Functions:
1. Gist extraction - Compress detailed memories to essential summaries
2. Contradiction detection - Find memories that conflict with each other
"""

import time
from datetime import datetime, timedelta
from typing import Optional

import re

from anima.core import Memory, ImpactLevel
from anima.dream.types import N3Result, GistResult, Contradiction, ScopeIssue, DreamConfig
from anima.embeddings import cosine_similarity
from anima.storage.sqlite import MemoryStore
from anima.storage.dissonance import DissonanceStore


def run_n3_processing(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str] = None,
    config: Optional[DreamConfig] = None,
    quiet: bool = False,
) -> N3Result:
    """
    Run N3 deep processing stage.

    1. Extract gist summaries for verbose memories
    2. Detect contradictions between similar memories
    3. Queue unresolvable contradictions for human help

    Args:
        store: Memory storage interface
        agent_id: Agent to process memories for
        project_id: Optional project filter
        config: Dream configuration
        quiet: Suppress output

    Returns:
        N3Result with gist and contradiction statistics
    """
    config = config or DreamConfig()
    start_time = time.time()

    if not quiet:
        print("N3: Deep processing...")

    # Get memories to process
    memories = _get_memories_for_processing(store, agent_id, project_id, config)

    if not quiet:
        print(f"   Found {len(memories)} memories for processing")

    if len(memories) == 0:
        return N3Result(
            gists_created=0,
            gist_results=[],
            contradictions_found=0,
            contradictions=[],
            dissonance_queue_additions=0,
            duration_seconds=time.time() - start_time,
            memories_processed=0,
        )

    # Phase 1: Gist extraction
    gist_results = []
    for memory in memories:
        if _needs_gist(memory, config):
            gist = _extract_gist(memory, config)
            if gist:
                gist_results.append(
                    GistResult(
                        memory_id=memory.id,
                        original_length=len(memory.content),
                        gist=gist,
                        gist_length=len(gist),
                    )
                )

    if not quiet:
        print(f"   Created {len(gist_results)} gist summaries")

    # Phase 2: Contradiction detection (candidates only - evaluated during REM)
    contradictions = []

    # Get memories with embeddings for semantic comparison
    memories_with_embeddings = store.get_memories_with_temporal_context(
        agent_id=agent_id,
        project_id=project_id,
        include_superseded=False,
    )

    # Filter to recent memories with embeddings
    cutoff = datetime.now() - timedelta(days=config.project_lookback_days)
    recent_with_embeddings = [m for m in memories_with_embeddings if m[2] is not None and _is_recent(m[3], cutoff)]

    # Compare pairs for contradictions
    for i, (mem_a_id, content_a, emb_a, _, _) in enumerate(recent_with_embeddings):
        for mem_b_id, content_b, emb_b, _, _ in recent_with_embeddings[i + 1 :]:
            similarity = cosine_similarity(emb_a, emb_b)

            # High similarity but potential negation = candidate contradiction
            if similarity >= config.n3_contradiction_threshold:
                contradiction = _detect_contradiction(
                    mem_a_id,
                    content_a,
                    mem_b_id,
                    content_b,
                    similarity,
                )

                if contradiction:
                    contradictions.append(contradiction)

    if not quiet:
        print(f"   Detected {len(contradictions)} contradiction candidates (to evaluate in REM)")

    # Phase 3: Memory scope validation
    scope_issues = []
    memories_validated = 0

    # Get known project names for scope detection
    known_projects = _get_known_project_names(store)

    # Get unvalidated memories
    unvalidated = store.get_unvalidated_memories(agent_id, limit=config.n2_process_limit)

    if not quiet and unvalidated:
        print(f"   Validating {len(unvalidated)} unvalidated memories...")

    for memory in unvalidated:
        issue = _detect_scope_issue(memory, known_projects)

        if issue:
            # Flag for human review
            scope_issues.append(issue)
        else:
            # Auto-validate (clear scope)
            store.mark_memory_validated(memory.id)
            memories_validated += 1

    # Queue scope issues as dissonances
    dissonance_store = DissonanceStore()
    scope_dissonances_added = 0
    for issue in scope_issues:
        if not dissonance_store.scope_issue_exists(issue.memory_id):
            dissonance_store.add_scope_issue(
                agent_id=agent_id,
                memory_id=issue.memory_id,
                description=issue.reason,
                suggested_region=issue.suggested_region,
                suggested_project_id=issue.suggested_project_id,
            )
            scope_dissonances_added += 1

    if not quiet:
        print(f"   Validated {memories_validated} memories, flagged {len(scope_issues)} for scope review")

    duration = time.time() - start_time

    return N3Result(
        gists_created=len(gist_results),
        gist_results=gist_results,
        contradictions_found=len(contradictions),
        contradictions=contradictions,
        dissonance_queue_additions=scope_dissonances_added,  # Now includes scope issues
        duration_seconds=duration,
        memories_processed=len(memories),
        memories_validated=memories_validated,
        scope_issues_found=len(scope_issues),
        scope_issues=scope_issues,
    )


def _is_recent(created_at: datetime, cutoff: datetime) -> bool:
    """Check if datetime is recent (handles timezone-aware vs naive)."""
    if created_at.tzinfo is not None:
        created_at = created_at.replace(tzinfo=None)
    return created_at >= cutoff


def _get_memories_for_processing(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str],
    config: DreamConfig,
) -> list[Memory]:
    """Get memories that might benefit from N3 processing."""
    # Get all non-superseded memories for the agent
    memories = store.get_memories_for_agent(
        agent_id=agent_id,
        project_id=project_id,
        include_superseded=False,
    )

    # Filter by lookback window
    cutoff = datetime.now() - timedelta(days=config.project_lookback_days)
    recent = [m for m in memories if _is_recent(m.created_at, cutoff)]

    return recent


def _needs_gist(memory: Memory, config: DreamConfig) -> bool:
    """Determine if memory needs gist extraction."""
    # Skip CRITICAL - keep full detail always
    if memory.impact == ImpactLevel.CRITICAL:
        return False

    # Only gist if content is long enough to benefit
    # Rough estimate: 4 chars per token, need at least 200 chars (50 tokens)
    if len(memory.content) < 200:
        return False

    # Target gist would be meaningless if original is already short
    target_gist_chars = config.n3_gist_max_tokens * 4
    if len(memory.content) <= target_gist_chars * 2:
        return False

    return True


def _extract_gist(memory: Memory, config: DreamConfig) -> Optional[str]:
    """
    Extract gist summary from memory using heuristics.

    For now, uses simple extraction rules. Future: local LLM.

    Strategy:
    1. Take first sentence (usually the hook/summary)
    2. Add any sentences with key signal words
    3. Truncate to target length
    """
    content = memory.content

    # Split into sentences (simple heuristic)
    sentences = _split_sentences(content)
    if not sentences:
        return None

    # Always include first sentence
    gist_parts = [sentences[0]]

    # Signal words that indicate important content
    key_signals = [
        "key insight",
        "important",
        "learned that",
        "realized",
        "discovered",
        "conclusion",
        "takeaway",
        "main point",
        "critical",
        "essential",
        "must",
        "always",
        "never",
    ]

    # Add sentences with signal words
    target_chars = config.n3_gist_max_tokens * 4
    current_length = len(gist_parts[0])

    for sentence in sentences[1:]:
        sentence_lower = sentence.lower()
        if any(signal in sentence_lower for signal in key_signals):
            if current_length + len(sentence) + 2 <= target_chars:
                gist_parts.append(sentence)
                current_length += len(sentence) + 2
            else:
                break

    gist = ". ".join(gist_parts)
    if not gist.endswith("."):
        gist += "."

    return gist


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences (simple heuristic)."""
    # Handle common abbreviations that shouldn't split
    text = text.replace("e.g.", "eg").replace("i.e.", "ie").replace("etc.", "etc")

    # Split on sentence-ending punctuation
    import re

    sentences = re.split(r"(?<=[.!?])\s+", text)

    # Clean up and filter empty
    sentences = [s.strip() for s in sentences if s.strip()]

    # Restore abbreviations
    sentences = [s.replace("eg", "e.g.").replace("ie", "i.e.").replace("etc", "etc.") for s in sentences]

    return sentences


def _detect_contradiction(
    mem_a_id: str,
    content_a: str,
    mem_b_id: str,
    content_b: str,
    similarity: float,
) -> Optional[Contradiction]:
    """
    Detect if two similar memories contradict each other.

    Heuristics:
    - Negation patterns ("X is" vs "X is not")
    - Opposite sentiment words
    - Temporal disagreement ("always" vs "never")

    Args:
        mem_a_id: ID of first memory
        content_a: Content of first memory
        mem_b_id: ID of second memory
        content_b: Content of second memory
        similarity: Cosine similarity between embeddings

    Returns:
        Contradiction if detected, None otherwise
    """
    content_a_lower = content_a.lower()
    content_b_lower = content_b.lower()

    # Negation words
    negation_words = [
        "not",
        "never",
        "don't",
        "doesn't",
        "isn't",
        "aren't",
        "wasn't",
        "weren't",
        "won't",
        "can't",
        "shouldn't",
        "wouldn't",
        "couldn't",
        "no longer",
        "anymore",
    ]

    a_has_negation = any(word in content_a_lower for word in negation_words)
    b_has_negation = any(word in content_b_lower for word in negation_words)

    # If one has negation and other doesn't = potential contradiction
    if a_has_negation != b_has_negation and similarity > 0.75:
        return Contradiction(
            memory_id_a=mem_a_id,
            memory_id_b=mem_b_id,
            content_a=content_a[:200] + ("..." if len(content_a) > 200 else ""),
            content_b=content_b[:200] + ("..." if len(content_b) > 200 else ""),
            description=f"Negation-based contradiction detected (similarity: {similarity:.2f})",
            similarity=similarity,
        )

    # Opposite absolutes ("always" vs "never", "everything" vs "nothing")
    opposite_pairs = [
        ("always", "never"),
        ("everything", "nothing"),
        ("everyone", "no one"),
        ("all", "none"),
        ("completely", "not at all"),
    ]

    for word_a, word_b in opposite_pairs:
        a_has_first = word_a in content_a_lower
        a_has_second = word_b in content_a_lower
        b_has_first = word_a in content_b_lower
        b_has_second = word_b in content_b_lower

        # If A has "always" and B has "never" (or vice versa)
        if (a_has_first and b_has_second) or (a_has_second and b_has_first):
            return Contradiction(
                memory_id_a=mem_a_id,
                memory_id_b=mem_b_id,
                content_a=content_a[:200] + ("..." if len(content_a) > 200 else ""),
                content_b=content_b[:200] + ("..." if len(content_b) > 200 else ""),
                description=f"Opposite absolutes ({word_a}/{word_b}) detected (similarity: {similarity:.2f})",
                similarity=similarity,
            )

    return None


def _get_known_project_names(store: MemoryStore) -> set[str]:
    """Get all known project names/IDs from the database."""
    projects = set()
    with store._connect() as conn:
        rows = conn.execute("SELECT id, name FROM projects").fetchall()
        for row in rows:
            projects.add(row["id"].lower())
            projects.add(row["name"].lower())
    return projects


def _detect_scope_issue(memory: Memory, known_projects: set[str]) -> Optional[ScopeIssue]:
    """
    Detect if a memory might be in the wrong region.

    Heuristics:
    - AGENT memories with project names/versions → might be PROJECT
    - PROJECT memories with generic learnings → might be AGENT

    Returns:
        ScopeIssue if potential misplacement detected, None otherwise
    """
    content_lower = memory.content.lower()
    current_region = memory.region.value

    # Version pattern: v0.1.2, v1.0, etc.
    version_pattern = r"\bv\d+\.\d+(?:\.\d+)?\b"
    has_version = bool(re.search(version_pattern, content_lower))

    # Check for project name mentions
    mentioned_projects = [p for p in known_projects if p in content_lower and len(p) > 3]

    # Generic learning signals (agent-wide insights)
    agent_signals = [
        "i learned",
        "key insight",
        "general principle",
        "always remember",
        "this applies to",
        "across projects",
        "matt's philosophy",
        "important lesson",
        "fundamental",
        "universal",
    ]
    has_agent_signals = any(signal in content_lower for signal in agent_signals)

    # Project-specific signals
    project_signals = [
        "in this project",
        "for this codebase",
        "commit",
        "release",
        "deployed",
        "this repo",
        "hud ",  # Common project abbreviation
        "api endpoint",
        "database schema",
    ]
    has_project_signals = any(signal in content_lower for signal in project_signals)

    # Achievement with version = likely project-specific
    achievement_signals = ["built", "released", "completed", "shipped", "implemented"]
    has_achievement = any(signal in content_lower for signal in achievement_signals)

    # Decision logic
    if current_region == "AGENT":
        # Agent memory with strong project signals
        if mentioned_projects and has_version and has_achievement:
            suggested_project = mentioned_projects[0] if mentioned_projects else None
            return ScopeIssue(
                memory_id=memory.id,
                content=memory.content[:200] + ("..." if len(memory.content) > 200 else ""),
                current_region=current_region,
                current_project_id=memory.project_id,
                suggested_region="PROJECT",
                suggested_project_id=suggested_project,
                reason=f"AGENT memory mentions project '{suggested_project}' with version number and achievement",
            )
        elif has_version and has_project_signals and not has_agent_signals:
            return ScopeIssue(
                memory_id=memory.id,
                content=memory.content[:200] + ("..." if len(memory.content) > 200 else ""),
                current_region=current_region,
                current_project_id=memory.project_id,
                suggested_region="PROJECT",
                suggested_project_id=None,  # Can't determine which project
                reason="AGENT memory has version number and project-specific signals without agent-wide learning",
            )

    elif current_region == "PROJECT":
        # Project memory with strong agent signals and no project specifics
        if has_agent_signals and not has_version and not has_project_signals:
            return ScopeIssue(
                memory_id=memory.id,
                content=memory.content[:200] + ("..." if len(memory.content) > 200 else ""),
                current_region=current_region,
                current_project_id=memory.project_id,
                suggested_region="AGENT",
                suggested_project_id=None,
                reason="PROJECT memory contains general learning without project-specific context",
            )

    return None
