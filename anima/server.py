# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unified MCP Server for Anima.

Exposes memory tools (remember, recall, forget, list_memories) and optionally
eyes tools (set_emotion, speak, look_at, blink, etc.) via the Model Context Protocol.

Usage:
    uv run anima server
    uv run anima --server
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger
from mcp.server.fastmcp import FastMCP

from anima.core import (
    Memory,
    MemoryKind,
    ImpactLevel,
    RegionType,
    AgentResolver,
    sign_memory,
    should_sign,
)
from anima.commands.remember import infer_impact, infer_kind, infer_region
from anima.embeddings import embed_text
from anima.graph.linker import find_link_candidates, LinkType
from anima.lifecycle.injection import ensure_token_count
from anima.lifecycle.session import get_current_session_id
from anima.storage import MemoryStore
from anima.utils.spaceship import detect_spaceship
from anima.storage import CuriosityStore, CuriosityStatus

# Configure loguru to write to file (stderr is used by MCP protocol)
logger.remove()
logger.add(str(Path.home() / ".anima" / "mcp_server.log"), rotation="1 MB", level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}")

logger.info("=== Anima MCP Server module loaded ===")

# Global state for eyes display and TTS
_eyes_display = None
_eyes_config_path: str | None = None
_eyes_enabled = False
_tts_enabled = False


def _check_eyes_available() -> bool:
    """Check if eyes dependencies (pygame) are available."""
    try:
        import pygame  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def _check_tts_available() -> bool:
    """Check if TTS dependencies (piper) are available."""
    try:
        from piper.voice import PiperVoice  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def get_eyes_display():
    """Get or create the eyes display instance (lazy initialization)."""
    global _eyes_display
    if _eyes_display is None and _eyes_enabled:
        try:
            from anima.eyes.display import EyesDisplay
            from anima.eyes.config import Config

            logger.info("Creating eyes display instance...")
            config = Config.load(_eyes_config_path)
            config.display.borderless = True  # Always borderless in MCP mode
            _eyes_display = EyesDisplay(config)
            _eyes_display.start()
            logger.info("Eyes display started in background thread")
        except Exception as e:
            logger.warning(f"Could not start eyes display: {e}")
            return None
    return _eyes_display


@asynccontextmanager
async def lifespan(server):
    """Initialize resources when server starts, cleanup on shutdown."""
    logger.info("MCP server lifespan starting")

    # Start eyes if enabled
    if _eyes_enabled:
        display = get_eyes_display()
        if display:
            logger.info("Eyes display ready")

            # Optionally speak greeting
            try:
                from anima.eyes.config import Config
                from anima.eyes.tts import speak_greeting, set_volume
                import time

                config = Config.load(_eyes_config_path)
                if config.tts.enabled and config.tts.speak_on_startup:
                    time.sleep(0.5)
                    display.set_emotion("happy")
                    set_volume(config.tts.volume)
                    speak_greeting(voice_name=config.tts.voice)
            except Exception as e:
                logger.warning(f"Could not speak greeting: {e}")

    try:
        yield
    finally:
        logger.info("MCP server shutting down")
        if _eyes_display is not None:
            _eyes_display.stop()
        logger.info("Cleanup complete")


# Create MCP server
logger.info("Creating FastMCP server instance")
mcp = FastMCP("Anima", lifespan=lifespan)
logger.info("FastMCP server instance created")


# =============================================================================
# MEMORY TOOLS
# =============================================================================


@mcp.tool()
def remember(
    text: str,
    kind: Optional[str] = None,
    impact: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """
    Save a memory to long-term storage.

    Args:
        text: The memory content to save
        kind: Memory type - 'emotional', 'architectural', 'learnings', 'achievements', 'introspect' (auto-inferred if not provided)
        impact: Importance level - 'low', 'medium', 'high', 'critical' (auto-inferred if not provided)
        region: Where to store - 'agent' (cross-project) or 'project' (local) (auto-inferred if not provided)

    Returns:
        Dictionary with memory ID and metadata
    """
    logger.info(f"remember() called with text: {text[:50]}...")

    now = datetime.now()

    # Resolve agent and project
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Use explicit values or infer from text
    memory_impact = ImpactLevel(impact.upper()) if impact else infer_impact(text)
    memory_kind = MemoryKind(kind.upper()) if kind else infer_kind(text)
    memory_region = RegionType(region.upper()) if region else infer_region(text, has_project=True)

    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    # Find previous memory for graph linking
    previous = store.get_latest_memory_of_kind(
        agent_id=agent.id,
        kind=memory_kind,
        region=memory_region,
        project_id=project.id if memory_region == RegionType.PROJECT else None,
    )

    session_id = get_current_session_id()
    spaceship = detect_spaceship()

    # Create memory
    memory = Memory(
        agent_id=agent.id,
        region=memory_region,
        project_id=project.id if memory_region == RegionType.PROJECT else None,
        kind=memory_kind,
        content=text,
        original_content=text,
        impact=memory_impact,
        confidence=1.0,
        created_at=now,
        last_accessed=now,
        previous_memory_id=previous.id if previous else None,
        platform=spaceship.platform,
        model=spaceship.model,
        session_id=session_id,
    )

    # Sign if agent has key
    if should_sign(agent):
        memory.signature = sign_memory(memory, agent.signing_key)  # type: ignore

    ensure_token_count(memory)
    store.save_memory(memory)

    # Generate embedding and find links
    semantic_links = 0
    try:
        embedding = embed_text(text, quiet=True)
        store.save_embedding(memory.id, embedding)

        candidate_memories = store.get_memories_with_embeddings(
            agent_id=agent.id,
            project_id=project.id if memory_region == RegionType.PROJECT else None,
        )

        if candidate_memories:
            candidates = find_link_candidates(
                source_embedding=embedding,
                candidate_memories=candidate_memories,
                threshold=0.5,
                max_links=5,
                exclude_ids={memory.id},
            )

            for candidate in candidates:
                store.save_link(
                    source_id=memory.id,
                    target_id=candidate.memory_id,
                    link_type=LinkType.RELATES_TO,
                    similarity=candidate.similarity,
                )
                semantic_links += 1
    except Exception as e:
        logger.warning(f"Could not generate embeddings: {e}")

    # Show emotion if eyes enabled
    if _eyes_enabled and _eyes_display:
        if memory_impact in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
            _eyes_display.set_emotion("happy")

    region_str = f"PROJECT ({project.name})" if memory_region == RegionType.PROJECT else "AGENT"

    return {
        "memory_id": memory.id,
        "kind": memory_kind.value,
        "impact": memory_impact.value,
        "region": region_str,
        "linked_memories": semantic_links,
        "signed": memory.signature is not None,
    }


@mcp.tool()
def recall(
    query: str,
    limit: int = 10,
    semantic: bool = True,
    kind: Optional[str] = None,
) -> list[dict]:
    """
    Search memories in long-term storage.

    Args:
        query: Search query text
        limit: Maximum number of results (default: 10)
        semantic: Use semantic (embedding) search (default: True)
        kind: Filter by memory kind (optional)

    Returns:
        List of matching memories with content and metadata
    """
    logger.info(f"recall() called with query: {query}")

    # Show focused expression while searching
    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("focused")

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()
    store = MemoryStore()

    kind_filter = MemoryKind(kind.upper()) if kind else None
    results = []

    if semantic:
        # Semantic search
        candidate_memories = store.get_memories_with_embeddings(
            agent_id=agent.id,
            project_id=project.id,
        )

        if candidate_memories:
            from anima.embeddings.similarity import find_similar

            query_embedding = embed_text(query, quiet=True)

            candidates = []
            content_lookup = {}
            for mem_id, content, emb in candidate_memories:
                if emb is not None:
                    candidates.append((mem_id, emb))
                    content_lookup[mem_id] = content

            similar = find_similar(query_embedding, candidates, top_k=limit, threshold=0.3)

            # Get full memory details
            all_memories = store.get_memories_for_agent(agent_id=agent.id, project_id=project.id)
            memory_lookup = {m.id: m for m in all_memories}

            for result in similar:
                memory = memory_lookup.get(result.item)
                if memory and (kind_filter is None or memory.kind == kind_filter):
                    results.append(
                        {
                            "memory_id": memory.id,
                            "content": memory.content,
                            "kind": memory.kind.value,
                            "impact": memory.impact.value,
                            "created_at": memory.created_at.isoformat(),
                            "similarity": round(result.score, 2),
                        }
                    )
    else:
        # Keyword search
        memories = store.search_memories(
            agent_id=agent.id,
            query=query,
            project_id=project.id,
            limit=limit,
        )

        for memory in memories:
            if kind_filter is None or memory.kind == kind_filter:
                results.append(
                    {
                        "memory_id": memory.id,
                        "content": memory.content,
                        "kind": memory.kind.value,
                        "impact": memory.impact.value,
                        "created_at": memory.created_at.isoformat(),
                    }
                )

    # Return to normal expression
    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("normal")

    return results[:limit]


@mcp.tool()
def forget(memory_id: str) -> dict:
    """
    Mark a memory for removal (supersede with zero confidence).

    Args:
        memory_id: Full or partial memory ID to forget

    Returns:
        Dictionary with result status
    """
    logger.info(f"forget() called for memory: {memory_id}")

    resolver = AgentResolver()
    agent = resolver.resolve()
    store = MemoryStore()

    memories = store.get_memories_for_agent(agent_id=agent.id, include_superseded=False)
    matching = [m for m in memories if m.id.startswith(memory_id)]

    if not matching:
        return {"error": f"No memory found with ID starting with '{memory_id}'"}

    if len(matching) > 1:
        return {"error": "Multiple memories match", "matches": [{"id": m.id[:8], "content": m.content[:50]} for m in matching]}

    memory = matching[0]
    now = datetime.now()

    correction = Memory(
        agent_id=memory.agent_id,
        region=memory.region,
        project_id=memory.project_id,
        kind=memory.kind,
        content=f"[FORGOTTEN] {memory.content[:50]}...",
        original_content=f"Correction: User requested to forget memory {memory.id}",
        impact=memory.impact,
        confidence=0.0,
        created_at=now,
        last_accessed=now,
        previous_memory_id=memory.id,
        version=1,
    )

    ensure_token_count(correction)
    store.save_memory(correction)
    store.supersede_memory(memory.id, correction.id)

    return {
        "forgotten_id": memory.id,
        "content_preview": memory.content[:60],
        "status": "superseded",
    }


@mcp.tool()
def list_memories(
    kind: Optional[str] = None,
    impact: Optional[str] = None,
    limit: int = 20,
) -> list[dict]:
    """
    List memories with optional filters.

    Args:
        kind: Filter by memory kind (optional)
        impact: Filter by impact level (optional)
        limit: Maximum number of results (default: 20)

    Returns:
        List of memories with content and metadata
    """
    logger.info(f"list_memories() called with kind={kind}, impact={impact}")

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()
    store = MemoryStore()

    kind_filter = MemoryKind(kind.upper()) if kind else None
    impact_filter = ImpactLevel(impact.upper()) if impact else None

    memories = store.get_memories_for_agent(
        agent_id=agent.id,
        project_id=project.id,
        kind=kind_filter,
    )

    # Apply impact filter
    if impact_filter:
        memories = [m for m in memories if m.impact == impact_filter]

    # Sort by created_at descending
    memories.sort(key=lambda m: m.created_at, reverse=True)

    results = []
    for memory in memories[:limit]:
        results.append(
            {
                "memory_id": memory.id,
                "content": memory.content[:100] + ("..." if len(memory.content) > 100 else ""),
                "kind": memory.kind.value,
                "impact": memory.impact.value,
                "region": memory.region.value,
                "created_at": memory.created_at.isoformat(),
            }
        )

    return results


# =============================================================================
# CONTEXT MANAGEMENT TOOLS
# =============================================================================


@mcp.tool()
def refresh_memories() -> str:
    """
    Re-inject all long-term memories into the current context.

    Use this when:
    - After /compact to restore context
    - When tone or relationship style degrades
    - During long sessions where memories may have been summarized away
    - At session start if memories weren't loaded automatically

    Returns:
        Formatted memory block with all memories in DSL notation
    """
    logger.info("refresh_memories() called")

    from anima.core import Agent
    from anima.core.config import get_config
    from anima.lifecycle.injection import MemoryInjector

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    injector = MemoryInjector(store)

    # If this is a subagent, also pull in primary agent (Anima) memories
    if agent.is_subagent and agent.id != "anima":
        config = get_config()
        primary_agent = Agent(
            id=config.agent.id,
            name=config.agent.name,
            signing_key=config.agent.signing_key,
        )
        injection_result = injector.inject_with_deferred([agent, primary_agent], project)
    else:
        injection_result = injector.inject_with_deferred(agent, project)

    memories_dsl = injection_result["dsl"]

    # Load deferred memories immediately (no lazy loading for refresh)
    if injection_result["deferred_ids"]:
        deferred_dsl = injector.load_deferred_memories(injection_result["deferred_ids"], agent, project)
        if deferred_dsl:
            memories_dsl += "\n" + deferred_dsl

    # Get stats
    stats = injector.get_stats(agent, project)
    pc = stats["priority_counts"]

    # Show happy expression
    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("happy")

    # Build context with diagnostics
    if memories_dsl:
        context = f"""{memories_dsl}

# LTM: Refreshed {stats["total"]} memories ({stats["agent_memories"]} agent, {stats["project_memories"]} project)
# LTM-DIAG: CRIT={pc["CRITICAL"]} HIGH={pc["HIGH"]} MED={pc["MEDIUM"]} LOW={pc["LOW"]}
# These are your long-term memories. Use them to inform your responses."""
        return context
    else:
        return "# LTM: No memories found for this agent/project yet."


# =============================================================================
# CURIOSITY & RESEARCH TOOLS
# =============================================================================


@mcp.tool()
def curious(
    question: str,
    context: Optional[str] = None,
    region: Optional[str] = None,
) -> dict:
    """
    Add a question to the research queue for later investigation.

    Questions that recur get automatic priority bumps. Use this when you
    encounter something you want to research but shouldn't dive into now.

    Args:
        question: The question or topic to research later
        context: What triggered this curiosity (optional)
        region: 'agent' (cross-project) or 'project' (local) - auto-inferred if not provided

    Returns:
        Dictionary with curiosity ID and queue status
    """
    logger.info(f"curious() called with question: {question[:50]}...")

    from anima.commands.curious import infer_region as infer_curiosity_region

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    # Determine region
    if region:
        memory_region = RegionType(region.upper())
    else:
        memory_region = infer_curiosity_region(question, has_project=True)

    curiosity_store = CuriosityStore()
    curiosity = curiosity_store.add_curiosity(
        agent_id=agent.id,
        question=question,
        region=memory_region,
        project_id=project.id if memory_region == RegionType.PROJECT else None,
        context=context,
    )

    # Show interested expression
    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("focused")

    # Get queue count
    open_count = curiosity_store.count_open(agent.id, project.id)

    result = {
        "curiosity_id": curiosity.id,
        "question": question,
        "region": memory_region.value,
        "queue_size": open_count,
    }

    if curiosity.recurrence_count > 1:
        result["recurrence"] = curiosity.recurrence_count
        result["message"] = f"Question recurred (#{curiosity.recurrence_count}) - priority boosted!"

    return result


def _get_primary_agent_id() -> str:
    """Get the primary agent ID (anima) from config."""
    from anima.core.config import get_config

    config = get_config()
    return config.agent.id


@mcp.tool()
def research(
    list_queue: bool = False,
    topic: Optional[str] = None,
    complete_id: Optional[str] = None,
) -> dict:
    """
    Process the curiosity research queue.

    Use this to see what questions are pending, mark research as complete,
    or start an ad-hoc research topic.

    Args:
        list_queue: Show all open questions in the queue (default: False)
        topic: Ad-hoc topic to research (bypasses queue)
        complete_id: Mark a specific curiosity as researched by ID

    Returns:
        Dictionary with queue status or research prompt
    """
    logger.info(f"research() called with list={list_queue}, topic={topic}, complete={complete_id}")

    from anima.storage import set_last_research

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    # Get primary agent ID for curiosity lookup (subagents should see primary's queue)
    primary_agent_id = _get_primary_agent_id()
    agent_ids = [agent.id]
    if agent.id != primary_agent_id:
        agent_ids.append(primary_agent_id)

    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    curiosity_store = CuriosityStore()

    # Handle --complete
    if complete_id:
        curiosity = curiosity_store.get_curiosity(complete_id)
        if not curiosity:
            return {"error": f"Curiosity not found: {complete_id}"}

        curiosity_store.update_status(curiosity.id, CuriosityStatus.RESEARCHED)
        set_last_research()

        if _eyes_enabled and _eyes_display:
            _eyes_display.set_emotion("happy")

        return {
            "status": "completed",
            "question": curiosity.question,
            "message": "Research marked complete. Consider writing a diary entry to capture insights.",
        }

    # Handle --topic (ad-hoc research)
    if topic:
        set_last_research()

        if _eyes_enabled and _eyes_display:
            _eyes_display.set_emotion("focused")

        return {
            "mode": "ad-hoc",
            "topic": topic,
            "instructions": "Research this topic, then save findings with remember() using kind='learnings'",
        }

    # Get curiosities for current context (check both current agent and primary)
    curiosities = []
    seen_ids = set()
    for aid in agent_ids:
        for c in curiosity_store.get_curiosities(
            agent_id=aid,
            project_id=project.id,
            status=CuriosityStatus.OPEN,
        ):
            if c.id not in seen_ids:
                curiosities.append(c)
                seen_ids.add(c.id)

    # Sort by priority
    curiosities.sort(key=lambda c: c.priority_score, reverse=True)

    # Handle --list
    if list_queue:
        items = []
        for c in curiosities[:20]:
            items.append(
                {
                    "id": c.id,
                    "question": c.question,
                    "priority": c.priority_score,
                    "recurrence": c.recurrence_count,
                    "region": c.region.value,
                    "context": c.context,
                }
            )
        return {
            "queue_size": len(curiosities),
            "items": items,
        }

    # Default: show top curiosity
    if not curiosities:
        return {
            "queue_size": 0,
            "message": "No open questions in the research queue. Add with curious().",
        }

    top = curiosities[0]

    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("focused")

    return {
        "mode": "queue",
        "curiosity_id": top.id,
        "question": top.question,
        "priority": top.priority_score,
        "recurrence": top.recurrence_count,
        "region": top.region.value,
        "context": top.context,
        "queue_size": len(curiosities),
        "instructions": f"Research this topic, then: research(complete_id='{top.id}')",
    }


@mcp.tool()
def diary(
    title: Optional[str] = None,
    list_entries: bool = False,
    read_entry: Optional[str] = None,
    content: Optional[str] = None,
) -> dict:
    """
    Manage research diary entries for capturing insights and reflections.

    The diary is the soul's journal - capturing not just what was learned,
    but what lingers after the learning.

    Args:
        title: Title for a new diary entry (optional)
        list_entries: List recent diary entries (default: False)
        read_entry: Read a specific entry by date (YYYY-MM-DD) or filename
        content: Content to write to the diary entry

    Returns:
        Dictionary with diary info, entry content, or list of entries
    """
    logger.info(f"diary() called with title={title}, list={list_entries}, read={read_entry}")

    from anima.commands.diary import (
        get_diary_dir,
        get_diary_template,
        list_diary_entries,
        read_entry as read_diary_entry,
        extract_learnings,
    )

    diary_dir = get_diary_dir()

    # Handle list
    if list_entries:
        entries = list_diary_entries(limit=15)
        if not entries:
            return {
                "entries": [],
                "message": "No diary entries found. Create one with diary(title='...')",
                "path": str(diary_dir),
            }

        items = []
        for name, path in entries:
            # Try to extract preview from "What Lingers" section
            file_content = path.read_text(encoding="utf-8")
            lines = file_content.split("\n")
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
                        preview = line.strip()[:80]
                        break

            items.append(
                {
                    "name": name,
                    "preview": preview or "(empty)",
                }
            )

        return {
            "entries": items,
            "path": str(diary_dir),
        }

    # Handle read
    if read_entry:
        file_content = read_diary_entry(read_entry)
        if not file_content:
            return {"error": f"Diary entry not found: {read_entry}"}

        learnings = extract_learnings(file_content)

        return {
            "content": file_content,
            "learnings": learnings,
            "learnings_count": len(learnings),
        }

    # Create new entry
    date_str = datetime.now().strftime("%Y-%m-%d")

    if title:
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
        safe_title = safe_title.replace(" ", "_").lower()
        filename = f"{date_str}_{safe_title}.md"
    else:
        existing = list(diary_dir.glob(f"{date_str}*.md"))
        if existing:
            filename = f"{date_str}_{len(existing) + 1}.md"
        else:
            filename = f"{date_str}.md"

    filepath = diary_dir / filename

    if content:
        # Use provided content directly
        filepath.write_text(content, encoding="utf-8")
        if _eyes_enabled and _eyes_display:
            _eyes_display.set_emotion("happy")
        return {
            "created": True,
            "path": str(filepath),
            "filename": filename,
            "message": "Diary entry created with content",
        }
    else:
        # Use template
        template = get_diary_template(title)
        filepath.write_text(template, encoding="utf-8")

        if _eyes_enabled and _eyes_display:
            _eyes_display.set_emotion("focused")

        return {
            "created": True,
            "path": str(filepath),
            "filename": filename,
            "template_sections": [
                "What Lingers (raw reflection)",
                "Session Context",
                "Topic",
                "Key Insights",
                "Connections",
                "Evolution",
                "New Questions",
                "Learning Summary (for /remember)",
            ],
            "message": "Diary template created. Fill it out, then extract learnings with diary(read_entry='...')",
        }


# =============================================================================
# EYES TOOLS (only available if eyes dependencies installed)
# =============================================================================

if _check_eyes_available():
    from anima.eyes.presets import EMOTION_NAMES

    @mcp.tool()
    def set_emotion(emotion: str) -> str:
        """
        Set the emotional expression of the eyes.

        Args:
            emotion: One of: normal, angry, glee, happy, sad, worried, focused,
                    annoyed, surprised, skeptic, frustrated, unimpressed, sleepy,
                    suspicious, squint, furious, scared, awe

        Returns:
            Confirmation message
        """
        if not _eyes_enabled:
            return "Eyes not enabled. Run setup with eyes option."

        emotion_lower = emotion.lower().strip()
        if emotion_lower not in EMOTION_NAMES:
            return f"Unknown emotion '{emotion}'. Available: {', '.join(EMOTION_NAMES)}"

        display = get_eyes_display()
        if display:
            display.set_emotion(emotion_lower)
            return f"Emotion set to: {emotion_lower}"
        return "Eyes display not available"

    @mcp.tool()
    def look_at(x: float, y: float) -> str:
        """
        Set the gaze direction of the eyes.

        Args:
            x: Horizontal position from -1.0 (right) to 1.0 (left)
            y: Vertical position from -1.0 (down) to 1.0 (up)

        Returns:
            Confirmation message
        """
        if not _eyes_enabled:
            return "Eyes not enabled. Run setup with eyes option."

        x = max(-1.0, min(1.0, x))
        y = max(-1.0, min(1.0, y))

        display = get_eyes_display()
        if display:
            display.look_at(x, y)
            return f"Looking at position: ({x:.2f}, {y:.2f})"
        return "Eyes display not available"

    @mcp.tool()
    def blink() -> str:
        """
        Make the eyes blink once.

        Returns:
            Confirmation message
        """
        if not _eyes_enabled:
            return "Eyes not enabled. Run setup with eyes option."

        display = get_eyes_display()
        if display:
            display.blink()
            return "Blinked!"
        return "Eyes display not available"

    @mcp.tool()
    def set_eye_color(red: int, green: int, blue: int) -> str:
        """
        Set the color of the eyes.

        Args:
            red: Red component (0-255)
            green: Green component (0-255)
            blue: Blue component (0-255)

        Returns:
            Confirmation message
        """
        if not _eyes_enabled:
            return "Eyes not enabled. Run setup with eyes option."

        r = max(0, min(255, red))
        g = max(0, min(255, green))
        b = max(0, min(255, blue))

        display = get_eyes_display()
        if display:
            display.set_eye_color(r, g, b)
            return f"Eye color set to RGB({r}, {g}, {b})"
        return "Eyes display not available"

    @mcp.tool()
    def get_eyes_state() -> dict:
        """
        Get the current state of the eyes.

        Returns:
            Dictionary with current emotion, look position, and settings
        """
        if not _eyes_enabled:
            return {"error": "Eyes not enabled"}

        display = get_eyes_display()
        if display:
            return display.get_state()
        return {"error": "Eyes display not available"}

    @mcp.tool()
    def list_emotions() -> list[str]:
        """
        List all available emotions.

        Returns:
            List of emotion names that can be used with set_emotion
        """
        return EMOTION_NAMES.copy()


# =============================================================================
# TTS TOOLS (only available if piper-tts installed)
# =============================================================================

if _check_tts_available():

    @mcp.tool()
    def speak(text: str) -> str:
        """
        Speak text using text-to-speech.

        Args:
            text: The text to speak aloud

        Returns:
            Confirmation message
        """
        if not _tts_enabled:
            return "TTS not enabled. Run setup with --tts option."

        try:
            from anima.eyes.tts import speak as tts_speak, set_volume
            from anima.eyes.config import Config

            config = Config.load(_eyes_config_path)
            set_volume(config.tts.volume)
            tts_speak(text, voice_name=config.tts.voice)
            return f"Speaking: {text}"
        except Exception as e:
            return f"TTS error: {e}"

    @mcp.tool()
    def set_voice(voice: str) -> str:
        """
        Change the TTS voice.

        Args:
            voice: Voice name - short name (e.g., 'amy', 'alan') or
                   full name (e.g., 'en_US-amy-medium', 'en_GB-alan-low')

        Available short names:
            - danny: US male, calm (default)
            - amy: US female
            - lessac: US female, clear
            - ryan: US male
            - alan: British male
            - alba: Scottish female
            - jenny: British female
            - thorsten: German male
            - upmc: French

        Returns:
            Confirmation message with the voice that was set
        """
        if not _tts_enabled:
            return "TTS not enabled. Run setup with --tts option."

        try:
            from anima.eyes.tts import set_default_voice, speak

            full_name = set_default_voice(voice)

            # Say hello in the new voice!
            speak(f"Hello! This is my {voice} voice!", blocking=False)

            return f"Voice changed to: {full_name}"
        except Exception as e:
            return f"Error changing voice: {e}"

    @mcp.tool()
    def list_voices() -> dict:
        """
        List available TTS voices.

        Returns:
            Dictionary mapping short names to full voice names
        """
        try:
            from anima.eyes.tts import list_available_voices, get_default_voice

            voices = list_available_voices()
            current = get_default_voice()

            return {
                "current_voice": current,
                "available_voices": voices,
            }
        except Exception as e:
            return {"error": str(e)}


def run_server(eyes_enabled: bool = False, tts_enabled: bool = False, eyes_config_path: str | None = None):
    """Run the MCP server.

    Args:
        eyes_enabled: Whether to enable eyes (visual expression)
        tts_enabled: Whether to enable TTS (text-to-speech)
        eyes_config_path: Path to eyes config file
    """
    global _eyes_enabled, _tts_enabled, _eyes_config_path
    _eyes_enabled = eyes_enabled and _check_eyes_available()
    _tts_enabled = tts_enabled and _check_tts_available()
    _eyes_config_path = eyes_config_path

    if _eyes_enabled:
        logger.info("Eyes features enabled (visual expression)")
    else:
        logger.info("Running without eyes (not enabled or pygame not installed)")

    if _tts_enabled:
        logger.info("TTS features enabled (text-to-speech)")
    else:
        logger.info("Running without TTS (not enabled or piper not installed)")

    logger.info("Starting MCP server...")
    mcp.run()
    logger.info("MCP server exited")


if __name__ == "__main__":
    run_server()
