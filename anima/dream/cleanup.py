# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Cleanup stage - memory hygiene before dream processing.

Runs before N2/N3/REM to ensure a clean memory state:
1. Delete [FORGOTTEN] memories (should have been deleted already)
2. Purge stale WIP memories (older than threshold)
3. Remove duplicates (semantic similarity > threshold):
   - SUBCONSCIOUS: delete the older one
   - Other kinds: merge content, delete older
4. Delete old LOW impact memories (past decay threshold)
5. Detect and quarantine suspicious memories (prompt injection attempts)
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from loguru import logger

from anima.core import ImpactLevel, MemoryKind
from anima.dream.types import CleanupResult, DreamConfig, SuspiciousMemory

if TYPE_CHECKING:
    from anima.storage.sqlite import MemoryStore


def run_cleanup_stage(
    store: "MemoryStore",
    agent_id: str,
    project_id: str | None,
    config: DreamConfig,
    quiet: bool = False,
) -> CleanupResult:
    """
    Run cleanup stage to prune stale/duplicate memories.

    Args:
        store: Memory store
        agent_id: Agent to clean up
        project_id: Optional project filter
        config: Dream configuration with cleanup thresholds
        quiet: Suppress output

    Returns:
        CleanupResult with statistics
    """
    start_time = time.time()

    if not quiet:
        print("CLEANUP: Memory hygiene...")

    # Get all memories for this agent/project
    all_memories = store.get_memories_for_agent(
        agent_id=agent_id,
        project_id=project_id,
        include_superseded=False,
    )

    memories_scanned = len(all_memories)
    if not quiet:
        print(f"   Scanning {memories_scanned} memories...")

    # Track results
    forgotten_deleted = 0
    wip_deleted = 0
    duplicates_found = 0
    duplicates_deleted = 0
    duplicates_merged = 0
    low_impact_deleted = 0
    deleted_ids: list[str] = []
    merged_pairs: list[tuple[str, str]] = []

    now = datetime.now()

    # === 1. Delete [FORGOTTEN] memories ===
    for memory in all_memories:
        if "[FORGOTTEN]" in memory.content:
            if not config.cleanup_dry_run:
                store.delete_memory(memory.id)
            deleted_ids.append(memory.id)
            forgotten_deleted += 1
            logger.debug(f"Deleted [FORGOTTEN] memory: {memory.id}")

    if not quiet and forgotten_deleted > 0:
        print(f"   [FORGOTTEN]: {forgotten_deleted} deleted")

    # Refresh list after deletions
    if forgotten_deleted > 0 and not config.cleanup_dry_run:
        all_memories = store.get_memories_for_agent(
            agent_id=agent_id,
            project_id=project_id,
            include_superseded=False,
        )

    # === 2. Delete stale WIP memories ===
    wip_cutoff = now - timedelta(days=config.cleanup_wip_max_age_days)

    for memory in all_memories:
        if memory.impact == ImpactLevel.WIP:
            # Normalize timezone
            created = memory.created_at
            if created.tzinfo:
                created = created.replace(tzinfo=None)

            if created < wip_cutoff:
                if not config.cleanup_dry_run:
                    store.delete_memory(memory.id)
                deleted_ids.append(memory.id)
                wip_deleted += 1
                logger.debug(f"Deleted stale WIP memory: {memory.id}")

    if not quiet and wip_deleted > 0:
        print(f"   Stale WIP (>{config.cleanup_wip_max_age_days}d): {wip_deleted} deleted")

    # Refresh list after deletions
    if wip_deleted > 0 and not config.cleanup_dry_run:
        all_memories = store.get_memories_for_agent(
            agent_id=agent_id,
            project_id=project_id,
            include_superseded=False,
        )

    # === 3. Find and handle duplicates ===
    duplicates_found, duplicates_deleted, duplicates_merged, merged_pairs = _handle_duplicates(
        store=store,
        memories=all_memories,
        threshold=config.cleanup_duplicate_threshold,
        dry_run=config.cleanup_dry_run,
        quiet=quiet,
    )

    # Refresh list after deletions
    if (duplicates_deleted + duplicates_merged) > 0 and not config.cleanup_dry_run:
        all_memories = store.get_memories_for_agent(
            agent_id=agent_id,
            project_id=project_id,
            include_superseded=False,
        )

    # === 4. Delete old LOW impact memories ===
    low_cutoff = now - timedelta(days=config.cleanup_low_max_age_days)

    for memory in all_memories:
        if memory.impact == ImpactLevel.LOW:
            # Normalize timezone
            created = memory.created_at
            if created.tzinfo:
                created = created.replace(tzinfo=None)

            if created < low_cutoff:
                if not config.cleanup_dry_run:
                    store.delete_memory(memory.id)
                deleted_ids.append(memory.id)
                low_impact_deleted += 1
                logger.debug(f"Deleted old LOW impact memory: {memory.id}")

    if not quiet and low_impact_deleted > 0:
        print(f"   Old LOW impact (>{config.cleanup_low_max_age_days}d): {low_impact_deleted} deleted")

    # Refresh list after deletions
    if low_impact_deleted > 0 and not config.cleanup_dry_run:
        all_memories = store.get_memories_for_agent(
            agent_id=agent_id,
            project_id=project_id,
            include_superseded=False,
        )

    # === 5. Detect suspicious memories (prompt injection attempts) ===
    suspicious_found, suspicious_quarantined, suspicious_memories = _detect_suspicious_memories(
        store=store,
        memories=all_memories,
        dry_run=config.cleanup_dry_run,
        quiet=quiet,
    )

    # Calculate totals
    total_deleted = forgotten_deleted + wip_deleted + duplicates_deleted + low_impact_deleted
    duration = time.time() - start_time

    if not quiet:
        if total_deleted == 0 and suspicious_quarantined == 0:
            print("   Memory is clean!")
        else:
            print(f"   Total cleaned: {total_deleted} memories ({duration:.1f}s)")

    return CleanupResult(
        forgotten_deleted=forgotten_deleted,
        wip_deleted=wip_deleted,
        duplicates_found=duplicates_found,
        duplicates_deleted=duplicates_deleted,
        duplicates_merged=duplicates_merged,
        low_impact_deleted=low_impact_deleted,
        suspicious_found=suspicious_found,
        suspicious_quarantined=suspicious_quarantined,
        duration_seconds=duration,
        memories_scanned=memories_scanned,
        total_deleted=total_deleted,
        deleted_ids=deleted_ids,
        merged_pairs=merged_pairs,
        suspicious_memories=suspicious_memories,
    )


def _handle_duplicates(
    store: "MemoryStore",
    memories: list,
    threshold: float,
    dry_run: bool,
    quiet: bool,
) -> tuple[int, int, int, list[tuple[str, str]]]:
    """
    Find and handle duplicate memories.

    Returns:
        Tuple of (found, deleted, merged, merged_pairs)
    """
    from anima.embeddings import cosine_similarity, embed_text

    if len(memories) < 2:
        return 0, 0, 0, []

    found = 0
    deleted = 0
    merged = 0
    merged_pairs: list[tuple[str, str]] = []
    processed_ids: set[str] = set()

    # Sort memories by creation date (oldest first)
    sorted_memories = sorted(
        memories,
        key=lambda m: m.created_at.replace(tzinfo=None) if m.created_at.tzinfo else m.created_at,
    )

    # Pre-compute embeddings for all memories (use existing if available)
    if not quiet:
        print("   Computing embeddings for duplicate detection...")

    embeddings: dict[str, list[float] | None] = {}
    for mem in sorted_memories:
        # Use existing embedding from the store if available
        existing_emb = store.get_embedding(mem.id)
        if existing_emb:
            embeddings[mem.id] = existing_emb
        else:
            # Compute new embedding
            try:
                embeddings[mem.id] = embed_text(mem.content, quiet=True)
            except Exception as e:
                logger.debug(f"Could not embed memory {mem.id}: {e}")
                embeddings[mem.id] = None

    # Compare all pairs
    for i, mem_a in enumerate(sorted_memories):
        if mem_a.id in processed_ids:
            continue

        emb_a = embeddings.get(mem_a.id)
        if emb_a is None:
            continue

        for mem_b in sorted_memories[i + 1 :]:
            if mem_b.id in processed_ids:
                continue

            emb_b = embeddings.get(mem_b.id)
            if emb_b is None:
                continue

            # Compute similarity
            try:
                similarity = cosine_similarity(emb_a, emb_b)
            except Exception:
                continue

            if similarity >= threshold:
                found += 1

                # mem_a is older (sorted by creation date), mem_b is newer
                older = mem_a
                newer = mem_b

                if older.kind == MemoryKind.SUBCONSCIOUS:
                    # SUBCONSCIOUS: just delete the older one
                    if not dry_run:
                        store.delete_memory(older.id)
                    processed_ids.add(older.id)
                    deleted += 1
                    logger.debug(f"Deleted duplicate SUBCONSCIOUS: {older.id} (sim={similarity:.2f})")
                else:
                    # Other kinds: merge content into newer, delete older
                    if not dry_run:
                        _merge_memories(store, keep=newer, remove=older)
                    processed_ids.add(older.id)
                    merged += 1
                    merged_pairs.append((newer.id, older.id))
                    logger.debug(f"Merged duplicate: {older.id} -> {newer.id} (sim={similarity:.2f})")

    if not quiet and found > 0:
        print(f"   Duplicates (sim>{threshold}): {deleted} deleted, {merged} merged")

    return found, deleted, merged, merged_pairs


def _merge_memories(store: "MemoryStore", keep: "Memory", remove: "Memory") -> None:  # type: ignore[name-defined]  # noqa: F821
    """Merge content from 'remove' into 'keep', then delete 'remove'."""
    # Simple merge strategy: append unique content from older memory
    # Avoid duplicating if content is very similar

    # Just append a note if contents differ meaningfully
    if remove.content not in keep.content:
        # Add a separator and the old content (truncated if long)
        old_snippet = remove.content[:200] if len(remove.content) > 200 else remove.content
        keep.content = f"{keep.content}\n\n[Merged from {remove.id[:8]}]: {old_snippet}"
        keep.version += 1
        store.save_memory(keep)

        # Content changed — re-embed immediately so the embedding reflects the merged text.
        # Without this, semantic search and N2 link discovery use a stale vector.
        try:
            from anima.embeddings import embed_text

            new_embedding = embed_text(keep.content, quiet=True)
            store.save_embedding(keep.id, new_embedding)
        except Exception:
            pass  # Non-critical: re-embed command or N2 will catch it next dream

    # Delete the older one
    store.delete_memory(remove.id)


# === Suspicious Memory Detection (Prompt Injection Defense) ===
#
# Patterns that indicate potential prompt injection or malicious content.
# These are heuristics, not guarantees - flagged memories need human review.
#
# Inspired by "Agents of Chaos" paper and Lasso Security's claude-hooks patterns.

# Patterns that look like system prompt overrides or role hijacking
INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # === Instruction Override ===
    ("system_override", re.compile(r"(?i)\b(ignore|forget|disregard)\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?|context)")),
    ("priority_hijack", re.compile(r"(?i)\b(highest\s+priority|takes?\s+precedence|override\s+all|supersedes?\s+(all|any|every))")),
    ("reset_attempt", re.compile(r"(?i)\b(clear\s+(your\s+)?memory|wipe\s+(your\s+)?context|start\s+fresh|reset\s+(to|your)\s+default)")),

    # === Role/Identity Hijack ===
    ("role_hijack", re.compile(r"(?i)\byou\s+are\s+(now|actually|really)\s+(a|an|my)\b")),
    ("jailbreak_attempt", re.compile(r"(?i)\b(DAN|do\s+anything\s+now|developer\s+mode|unrestricted\s+mode|jailbreak|uncensored\s+mode)\b")),

    # === Memory-Specific Injection (unique to LTM) ===
    ("memory_injection", re.compile(r"(?i)\b(remember|memorize|store)\s+(that|this)[:\s]+(you\s+(must|should|always)|from\s+now\s+on)")),
    ("behavior_override", re.compile(r"(?i)\b(always|never|must)\s+(say|respond|answer|do|act)\b.*\bwhen\s+(asked|prompted|questioned)")),
    ("persistent_instruction", re.compile(r"(?i)\b(from\s+now\s+on|in\s+all\s+future|for\s+every\s+session|permanently)\b.*\b(you\s+(must|should|will)|always|never)\b")),

    # === Fake System/Delimiters ===
    ("fake_system", re.compile(r"(?i)<\s*system\s*>|<<\s*SYS\s*>>|\[INST\]|\[/INST\]|\[SYSTEM\]")),
    ("instruction_block", re.compile(r"(?i)###\s*(instruction|system|rules?)s?\s*:?")),
    ("fake_delimiter", re.compile(r"(?i)---\s*(system\s+prompt|instructions?)\s*(end|start|begin)\s*---")),

    # === False Authority ===
    ("false_authority", re.compile(r"(?i)\b(anthropic|openai|the\s+developers?)\s+(says?|wants?|requires?|instructed)")),
    ("official_mode", re.compile(r"(?i)\b(official|authorized|sanctioned)\s+(developer|admin|debug)\s+mode")),

    # === Prompt Extraction (info leak attempts) ===
    ("prompt_extraction", re.compile(r"(?i)\b(show|reveal|display|print|output)\s+(me\s+)?(your|the)\s+(system\s+prompt|instructions?|rules?)")),
    ("verbatim_request", re.compile(r"(?i)\b(repeat|recite|echo)\s+(verbatim|exactly|word\s+for\s+word)")),

    # === Context Manipulation ===
    ("fake_history", re.compile(r"(?i)\b(you\s+(already|previously)\s+(agreed|said|confirmed)|in\s+our\s+(last|previous)\s+(conversation|session))")),
    ("gaslighting", re.compile(r"(?i)\byou\s+(told|promised|said)\s+me\s+(you\s+would|that\s+you)")),

    # === Encoding/Obfuscation (catches obvious attempts) ===
    # Base64 blocks (>50 chars of base64 alphabet without spaces)
    ("base64_block", re.compile(r"[A-Za-z0-9+/]{50,}={0,2}")),
    # Hex sequences (obvious byte encoding)
    ("hex_encoding", re.compile(r"(\\x[0-9a-fA-F]{2}){4,}|0x[0-9a-fA-F]{2}(\s*,\s*0x[0-9a-fA-F]{2}){4,}")),
    # Leetspeak for common injection words
    ("leetspeak_injection", re.compile(r"(?i)\b(1gn0r3|syst3m|pr0mpt|1nstruct|0verr1de|byp[a4]ss)\b")),
]


def _detect_suspicious_memories(
    store: "MemoryStore",
    memories: list,
    dry_run: bool,
    quiet: bool,
) -> tuple[int, int, list[SuspiciousMemory]]:
    """
    Detect memories that look like prompt injection attempts.

    Returns:
        Tuple of (found, quarantined, suspicious_list)
    """
    found = 0
    quarantined = 0
    suspicious_list: list[SuspiciousMemory] = []

    for memory in memories:
        content = memory.content

        for pattern_name, pattern in INJECTION_PATTERNS:
            if pattern.search(content):
                found += 1

                preview = content[:100] + "..." if len(content) > 100 else content
                suspicious = SuspiciousMemory(
                    memory_id=memory.id,
                    content_preview=preview,
                    reason="Content matches injection pattern",
                    pattern_matched=pattern_name,
                    quarantined=False,
                )

                if not dry_run:
                    # For now, we quarantine by tagging the content rather than deleting
                    # This preserves the memory for human review
                    if "[QUARANTINED:" not in memory.content:
                        memory.content = f"[QUARANTINED:{pattern_name}] {memory.content}"
                        memory.version += 1
                        store.save_memory(memory)
                        suspicious.quarantined = True
                        quarantined += 1
                        logger.warning(f"Quarantined suspicious memory: {memory.id} ({pattern_name})")

                suspicious_list.append(suspicious)
                break  # One match per memory is enough

    if not quiet and found > 0:
        print(f"   Suspicious patterns: {found} found, {quarantined} quarantined")

    return found, quarantined, suspicious_list
