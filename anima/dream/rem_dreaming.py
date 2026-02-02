# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
REM - Lucid Dreaming Stage

Character: Wandering, associative, unconstrained. The poet finding unexpected rhymes.

This is a LUCID dream - I'm aware I'm dreaming and consciously shape the content.
The code gathers materials, I provide the actual reflection.

Functions:
1. gather_dream_materials() - Collect raw materials for reflection
2. create_dream_template() - Create markdown template with materials
3. run_rem_dreaming() - Orchestrate the gathering and template creation

The actual dream content is written conversationally, not automated.
"""

import random
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from anima.dream.types import (
    REMResult,
    DreamMaterials,
    MemoryPair,
    IncompleteThought,
    DreamConfig,
)
from anima.embeddings import cosine_similarity
from anima.storage.sqlite import MemoryStore


def gather_dream_materials(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str] = None,
    config: Optional[DreamConfig] = None,
    since_last_dream: Optional[datetime] = None,
) -> DreamMaterials:
    """
    Gather raw materials for lucid dreaming.

    This collects the "ingredients" but doesn't generate insights.
    The actual reflection happens conversationally.

    Args:
        store: Memory storage interface
        agent_id: ID of agent doing the dreaming
        project_id: Optional project ID for context
        config: Dream configuration
        since_last_dream: If provided, only gather materials since this timestamp.
                         If None, falls back to config lookback_days.

    Returns:
        DreamMaterials with memory pairs, themes, incomplete thoughts
    """
    config = config or DreamConfig()

    # Gather memories with embeddings
    memories = store.get_memories_with_temporal_context(
        agent_id=agent_id,
        project_id=project_id,
        include_superseded=False,
    )

    # Determine cutoff: since_last_dream takes priority over lookback_days
    if since_last_dream is not None:
        memory_cutoff = since_last_dream
        diary_cutoff = since_last_dream
    else:
        memory_cutoff = datetime.now() - timedelta(days=config.project_lookback_days)
        diary_cutoff = datetime.now() - timedelta(days=config.diary_lookback_days)

    def is_recent_memory(created_at: datetime) -> bool:
        """Check if memory is within lookback window."""
        if created_at.tzinfo is not None:
            created_at = created_at.replace(tzinfo=None)
        cutoff = memory_cutoff.replace(tzinfo=None) if memory_cutoff.tzinfo else memory_cutoff
        return created_at >= cutoff

    # Get all memories with embeddings (for random sampling)
    all_with_embeddings = [m for m in memories if m[2] is not None]

    # Filter to recent memories (since last dream or lookback window)
    recent_memories = [m for m in all_with_embeddings if is_recent_memory(m[3])]

    # Load recent diary entries
    recent_diaries = _load_recent_diary_entries(since=diary_cutoff)

    # DREAM COMPOSITION: Recent material + random older memories
    # Like human dreams: process new events AND recombine old memories
    recent_ids = {m[0] for m in recent_memories}
    older_memories = [m for m in all_with_embeddings if m[0] not in recent_ids]

    # Sample random older memories to mix in (the "weird dream" component)
    random_sample_size = min(10, len(older_memories))
    random_old_memories = random.sample(older_memories, random_sample_size) if older_memories else []

    # Combine: all recent + random old
    memories_with_embeddings = recent_memories + random_old_memories

    # Also mix in some random old diaries
    random_old_diaries = _load_random_diary_entries(limit=3, exclude_recent=diary_cutoff)
    diary_entries = recent_diaries + random_old_diaries

    # 1. Find distant memory pairs (low similarity = interesting to connect)
    distant_pairs = _find_distant_pairs(
        memories_with_embeddings,
        threshold=config.rem_association_distance,
        max_pairs=5,
    )

    # 2. Find incomplete thoughts
    incomplete_thoughts = _find_incomplete_thoughts(memories)

    # 3. Extract recurring themes
    recurring_themes = _extract_recurring_themes(memories, min_count=3)

    # 4. Get diary snippets for pattern mining
    diary_snippets = [(date, _get_excerpt(content, max_len=200)) for date, content in diary_entries[:5]]

    return DreamMaterials(
        distant_pairs=distant_pairs,
        incomplete_thoughts=incomplete_thoughts,
        recurring_themes=recurring_themes[:10],  # Top 10 themes
        diary_snippets=diary_snippets,
        total_memories=len(memories_with_embeddings),
        total_diary_entries=len(diary_entries),
        recent_memories_count=len(recent_memories),
        random_old_memories_count=len(random_old_memories),
        recent_diaries_count=len(recent_diaries),
        random_old_diaries_count=len(random_old_diaries),
    )


def create_dream_template(
    materials: DreamMaterials,
    agent_id: str,
) -> Path:
    """
    Create a dream journal template with materials for reflection.

    The template has sections for:
    - Dream materials (auto-filled)
    - My reflections (to be filled conversationally)

    Args:
        materials: Gathered dream materials
        agent_id: Agent ID for attribution

    Returns:
        Path to created template file
    """
    dream_dir = Path.home() / ".anima" / "dream_journal"
    dream_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H%M")
    template_path = dream_dir / f"{today}_dream_{timestamp}.md"

    # Describe the dream composition
    dream_desc = []
    if materials.recent_memories_count > 0:
        dream_desc.append(f"{materials.recent_memories_count} new memories")
    if materials.random_old_memories_count > 0:
        dream_desc.append(f"{materials.random_old_memories_count} random old memories")
    if materials.recent_diaries_count > 0:
        dream_desc.append(f"{materials.recent_diaries_count} new diary entries")
    if materials.random_old_diaries_count > 0:
        dream_desc.append(f"{materials.random_old_diaries_count} random old diaries")

    composition = " + ".join(dream_desc) if dream_desc else "wandering through the archives"

    lines = [
        f"# Dream Journal - {today}",
        "",
        f"*Lucid dream session at {datetime.now().strftime('%H:%M')}*",
        "",
        "---",
        "",
        "## Dream Materials",
        "",
        f"*Dream composition: {composition}*",
        "",
    ]

    # Distant memory pairs section
    if materials.distant_pairs:
        lines.extend(
            [
                "### Memory Pairs to Connect",
                "",
                "*These memories are semantically distant - what unexpected connections exist?*",
                "",
            ]
        )
        for i, pair in enumerate(materials.distant_pairs, 1):
            lines.extend(
                [
                    f"**Pair {i}** (similarity: {pair.similarity:.2f})",
                    "",
                    f"> **A:** {pair.memory_a_content[:300]}{'...' if len(pair.memory_a_content) > 300 else ''}",
                    "",
                    f"> **B:** {pair.memory_b_content[:300]}{'...' if len(pair.memory_b_content) > 300 else ''}",
                    "",
                ]
            )

    # Incomplete thoughts section
    if materials.incomplete_thoughts:
        lines.extend(
            [
                "### Incomplete Thoughts",
                "",
                "*These thoughts were left unfinished - what's the answer?*",
                "",
            ]
        )
        for thought in materials.incomplete_thoughts[:5]:
            lines.append(f"- **[{thought.signal_type}]** {thought.snippet}")
        lines.append("")

    # Recurring themes section
    if materials.recurring_themes:
        lines.extend(
            [
                "### Recurring Themes",
                "",
                f"*Words that keep appearing: {', '.join(materials.recurring_themes)}*",
                "",
            ]
        )

    # Diary snippets section
    if materials.diary_snippets:
        lines.extend(
            [
                "### Recent Diary Excerpts",
                "",
            ]
        )
        for date, excerpt in materials.diary_snippets:
            lines.extend(
                [
                    f"**{date}:**",
                    f"> {excerpt}",
                    "",
                ]
            )

    # Reflection sections (to be filled conversationally)
    lines.extend(
        [
            "---",
            "",
            "## My Reflections",
            "",
            "### Distant Connections",
            "",
            "*What unexpected links do I see between the memory pairs above?*",
            "",
            "[To be filled during lucid dream...]",
            "",
            "### Questions That Emerged",
            "",
            "*What new curiosities arose from contemplating these materials?*",
            "",
            "[To be filled during lucid dream...]",
            "",
            "### Self-Observations",
            "",
            "*What patterns do I notice about how I think, feel, or work?*",
            "",
            "[To be filled during lucid dream...]",
            "",
            "### What Lingers",
            "",
            "*The raw residue - what stays with me after this dream?*",
            "",
            "[To be filled during lucid dream...]",
            "",
            "---",
            "",
            '*"Dreams are divergent, not convergent. They explore, connect, and create."*',
            "",
            f"— Agent {agent_id[:8]}, {today}",
        ]
    )

    content = "\n".join(lines)
    template_path.write_text(content, encoding="utf-8")

    return template_path


def run_rem_dreaming(
    store: MemoryStore,
    agent_id: str,
    project_id: Optional[str] = None,
    config: Optional[DreamConfig] = None,
    quiet: bool = False,
    since_last_dream: Optional[datetime] = None,
) -> REMResult:
    """
    Run REM lucid dreaming stage.

    This gathers materials and creates a template for reflection.
    The actual dream content is filled in conversationally.

    Args:
        store: Memory storage interface
        agent_id: ID of agent doing the dreaming
        project_id: Optional project ID for context
        config: Dream configuration
        quiet: Suppress output
        since_last_dream: If provided, only process materials since this timestamp

    Returns:
        REMResult with materials info and template path
    """
    config = config or DreamConfig()
    start_time = time.time()

    if not quiet:
        print("REM: Entering lucid dream state...")
        if since_last_dream:
            print(f"   (Gathering materials since last dream: {since_last_dream.strftime('%Y-%m-%d %H:%M')})")
        else:
            print("   (Gathering dream materials...)")

    # Gather materials
    materials = gather_dream_materials(
        store=store,
        agent_id=agent_id,
        project_id=project_id,
        config=config,
        since_last_dream=since_last_dream,
    )

    if not quiet:
        # Show dream composition breakdown
        parts = []
        if materials.recent_memories_count > 0:
            parts.append(f"{materials.recent_memories_count} new")
        if materials.random_old_memories_count > 0:
            parts.append(f"{materials.random_old_memories_count} random old")
        mem_desc = " + ".join(parts) if parts else "0"
        print(f"   Memories: {mem_desc}")

        parts = []
        if materials.recent_diaries_count > 0:
            parts.append(f"{materials.recent_diaries_count} new")
        if materials.random_old_diaries_count > 0:
            parts.append(f"{materials.random_old_diaries_count} random old")
        diary_desc = " + ".join(parts) if parts else "0"
        print(f"   Diaries: {diary_desc}")

        print(f"   Found {len(materials.distant_pairs)} memory pairs to reflect on")
        print(f"   Found {len(materials.incomplete_thoughts)} incomplete thoughts")

    # Create template
    template_path = create_dream_template(materials, agent_id)
    materials.template_path = str(template_path)

    if not quiet:
        print(f"   Created dream template: {template_path.name}")
        print()
        print("   Template ready for reflection.")
        print("   The actual dream happens conversationally - say 'good night' to dream!")

    duration = time.time() - start_time

    # Return minimal result - the real content comes from conversation
    return REMResult(
        distant_associations=[],  # Filled conversationally
        generated_questions=[],  # Filled conversationally
        self_model_updates=[],  # Filled conversationally
        diary_patterns_found=materials.recurring_themes,
        dream_journal_path=str(template_path),
        curiosity_queue_additions=0,
        duration_seconds=duration,
        iterations_completed=1,  # Template creation = 1 iteration
    )


def _find_distant_pairs(
    memories: list[tuple],
    threshold: float,
    max_pairs: int,
) -> list[MemoryPair]:
    """Find memory pairs with low similarity (distant concepts)."""
    pairs = []

    if len(memories) < 2:
        return pairs

    # Sample random pairs
    attempts = min(50, len(memories) * 2)
    for _ in range(attempts):
        if len(memories) >= 2:
            a, b = random.sample(memories, 2)
            mem_a_id, content_a, emb_a, _, _ = a
            mem_b_id, content_b, emb_b, _, _ = b

            similarity = cosine_similarity(emb_a, emb_b)

            # We want LOW similarity (distant) but not zero
            if 0.1 < similarity < threshold:
                pairs.append(
                    MemoryPair(
                        memory_a_id=mem_a_id,
                        memory_a_content=content_a,
                        memory_b_id=mem_b_id,
                        memory_b_content=content_b,
                        similarity=similarity,
                    )
                )

        if len(pairs) >= max_pairs:
            break

    # Sort by similarity (lowest first = most interesting)
    pairs.sort(key=lambda p: p.similarity)
    return pairs[:max_pairs]


def _find_incomplete_thoughts(memories: list[tuple]) -> list[IncompleteThought]:
    """Find incomplete thoughts in memories."""
    thoughts = []

    signals = [
        ("I wonder", "wonder"),
        ("TODO:", "todo"),
        ("need to research", "research"),
        ("not sure", "uncertain"),
        ("unclear", "unclear"),
        ("what if", "counterfactual"),
        ("should explore", "explore"),
        ("might be worth", "potential"),
        ("?", "question"),
    ]

    for mem_id, content, *_ in memories:
        content_lower = content.lower()
        for signal, signal_type in signals:
            if signal.lower() in content_lower:
                # Extract surrounding context
                idx = content_lower.find(signal.lower())
                start = max(0, idx - 30)
                end = min(len(content), idx + len(signal) + 100)
                snippet = content[start:end].strip()

                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."

                thoughts.append(
                    IncompleteThought(
                        memory_id=mem_id,
                        snippet=snippet,
                        signal_type=signal_type,
                    )
                )
                break  # One per memory

    return thoughts[:10]  # Limit


def _extract_recurring_themes(memories: list[tuple], min_count: int) -> list[str]:
    """Extract recurring keywords from memories."""
    stopwords = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "and",
        "in",
        "that",
        "it",
        "for",
        "with",
        "on",
        "as",
        "at",
        "by",
        "this",
        "from",
        "be",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "can",
        "must",
        "shall",
        "being",
        "been",
        "am",
        "or",
        "if",
        "but",
        "not",
        "no",
        "so",
        "than",
        "too",
        "very",
        "just",
        "also",
        "only",
        "then",
        "now",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "its",
        "my",
        "your",
        "our",
        "their",
        "his",
        "her",
        "we",
        "they",
        "you",
        "me",
        "him",
        "them",
        "us",
        "i",
        "about",
        "into",
        "through",
    }

    word_freq: dict[str, int] = {}

    for _, content, *_ in memories:
        words = content.lower().split()
        for word in words:
            word = word.strip(".,!?;:()[]{}\"'")
            if len(word) > 4 and word not in stopwords:
                word_freq[word] = word_freq.get(word, 0) + 1

    # Filter by minimum count and sort by frequency
    recurring = [word for word, count in word_freq.items() if count >= min_count]
    recurring.sort(key=lambda w: word_freq[w], reverse=True)

    return recurring


def _load_recent_diary_entries(since: Optional[datetime] = None, lookback_days: int = 7) -> list[tuple[str, str]]:
    """Load diary entries since a given date or within lookback days.

    Args:
        since: If provided, load entries since this datetime.
        lookback_days: Fallback if since not provided (default: 7)

    Returns:
        List of (filename_stem, content) tuples
    """
    diary_dir = Path.home() / ".anima" / "diary"
    entries = []

    if not diary_dir.exists():
        return entries

    # Calculate cutoff date
    if since is not None:
        cutoff = since
    else:
        cutoff = datetime.now() - timedelta(days=lookback_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    for path in sorted(diary_dir.glob("*.md"), reverse=True):
        try:
            # Diary files are named YYYY-MM-DD_title.md
            # Extract date from filename
            filename = path.stem
            if len(filename) >= 10 and filename[4] == "-" and filename[7] == "-":
                file_date = filename[:10]
                if file_date >= cutoff_str:
                    content = path.read_text(encoding="utf-8")
                    entries.append((filename, content))
        except Exception:
            continue

    return entries


def _load_random_diary_entries(
    limit: int = 5,
    exclude_recent: Optional[datetime] = None,
) -> list[tuple[str, str]]:
    """Load random older diary entries for dream recombination.

    Args:
        limit: Maximum entries to return
        exclude_recent: If provided, exclude entries after this date

    Returns:
        List of (filename_stem, content) tuples
    """
    diary_dir = Path.home() / ".anima" / "diary"
    entries = []

    if not diary_dir.exists():
        return entries

    exclude_str = exclude_recent.strftime("%Y-%m-%d") if exclude_recent else None

    for path in diary_dir.glob("*.md"):
        try:
            filename = path.stem
            if len(filename) >= 10 and filename[4] == "-" and filename[7] == "-":
                file_date = filename[:10]
                # Only include older entries (before cutoff)
                if exclude_str is None or file_date < exclude_str:
                    content = path.read_text(encoding="utf-8")
                    entries.append((filename, content))
        except Exception:
            continue

    # Random sample
    if len(entries) <= limit:
        return entries
    return random.sample(entries, limit)


def _get_excerpt(content: str, max_len: int = 200) -> str:
    """Get a short excerpt from content."""
    # Skip frontmatter and headers
    lines = content.split("\n")
    text_lines = [line for line in lines if line.strip() and not line.startswith("#") and not line.startswith("---")]
    text = " ".join(text_lines)

    if len(text) > max_len:
        return text[:max_len] + "..."
    return text
