# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unified MCP Server for Anima.

Token-optimized: Uses consolidated tools to minimize context overhead.
- memory(action, ...) - remember/recall/forget/list/refresh
- curiosity(action, ...) - add/research/diary/list

Usage:
    uv run anima server
    uv run anima --server
"""

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from loguru import logger
from mcp.server.fastmcp import FastMCP

from anima.core import (
    Memory,
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
# CONSOLIDATED MEMORY TOOL
# =============================================================================


@mcp.tool()
def memory(
    action: str,
    text: str = "",
    query: str = "",
    id: str = "",
    limit: int = 10,
) -> dict:
    """LTM operations. action: remember|recall|forget|list|refresh"""
    logger.info(f"memory({action}) called")

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()
    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    if action == "remember":
        return _do_remember(text, agent, project, store)
    elif action == "recall":
        return _do_recall(query or text, limit, agent, project, store)
    elif action == "forget":
        return _do_forget(id, agent, store)
    elif action == "list":
        return _do_list(limit, agent, project, store)
    elif action == "refresh":
        return _do_refresh(agent, project, store)
    else:
        return {"error": f"Unknown action: {action}. Use: remember|recall|forget|list|refresh"}


def _do_remember(text: str, agent, project, store: MemoryStore) -> dict:
    """Save a memory."""
    if not text:
        return {"error": "text required for remember"}

    now = datetime.now()
    memory_impact = infer_impact(text)
    memory_kind = infer_kind(text)
    memory_region = infer_region(text, has_project=True)

    previous = store.get_latest_memory_of_kind(
        agent_id=agent.id,
        kind=memory_kind,
        region=memory_region,
        project_id=project.id if memory_region == RegionType.PROJECT else None,
    )

    session_id = get_current_session_id()
    spaceship = detect_spaceship()

    mem = Memory(
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

    if should_sign(agent):
        mem.signature = sign_memory(mem, agent.signing_key)

    ensure_token_count(mem)
    store.save_memory(mem)

    # Generate embedding and find links
    semantic_links = 0
    try:
        embedding = embed_text(text, quiet=True)
        store.save_embedding(mem.id, embedding)

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
                exclude_ids={mem.id},
            )

            for candidate in candidates:
                store.save_link(
                    source_id=mem.id,
                    target_id=candidate.memory_id,
                    link_type=LinkType.RELATES_TO,
                    similarity=candidate.similarity,
                )
                semantic_links += 1
    except Exception as e:
        logger.warning(f"Could not generate embeddings: {e}")

    if _eyes_enabled and _eyes_display:
        if memory_impact in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
            _eyes_display.set_emotion("happy")

    return {
        "id": mem.id[:8],
        "kind": memory_kind.value,
        "impact": memory_impact.value,
        "links": semantic_links,
    }


def _do_recall(query: str, limit: int, agent, project, store: MemoryStore) -> dict:
    """Search memories."""
    if not query:
        return {"error": "query required for recall"}

    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("focused")

    candidate_memories = store.get_memories_with_embeddings(
        agent_id=agent.id,
        project_id=project.id,
    )

    results = []
    if candidate_memories:
        from anima.embeddings.similarity import find_similar

        query_embedding = embed_text(query, quiet=True)

        candidates = []
        for mem_id, content, emb in candidate_memories:
            if emb is not None:
                candidates.append((mem_id, emb))

        similar = find_similar(query_embedding, candidates, top_k=limit, threshold=0.3)

        all_memories = store.get_memories_for_agent(agent_id=agent.id, project_id=project.id)
        memory_lookup = {m.id: m for m in all_memories}

        for result in similar:
            mem = memory_lookup.get(result.item)
            if mem:
                results.append(
                    {
                        "id": mem.id[:8],
                        "content": mem.content[:200],
                        "kind": mem.kind.value,
                        "score": round(result.score, 2),
                    }
                )

    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("normal")

    return {"results": results[:limit], "count": len(results)}


def _do_forget(memory_id: str, agent, store: MemoryStore) -> dict:
    """Forget a memory."""
    if not memory_id:
        return {"error": "id required for forget"}

    memories = store.get_memories_for_agent(agent_id=agent.id, include_superseded=False)
    matching = [m for m in memories if m.id.startswith(memory_id)]

    if not matching:
        return {"error": f"No memory found: {memory_id}"}
    if len(matching) > 1:
        return {"error": "Multiple matches", "ids": [m.id[:8] for m in matching]}

    mem = matching[0]
    now = datetime.now()

    correction = Memory(
        agent_id=mem.agent_id,
        region=mem.region,
        project_id=mem.project_id,
        kind=mem.kind,
        content=f"[FORGOTTEN] {mem.content[:50]}...",
        original_content=f"Correction: User requested to forget memory {mem.id}",
        impact=mem.impact,
        confidence=0.0,
        created_at=now,
        last_accessed=now,
        previous_memory_id=mem.id,
        version=1,
    )

    ensure_token_count(correction)
    store.save_memory(correction)
    store.supersede_memory(mem.id, correction.id)

    return {"forgotten": mem.id[:8], "preview": mem.content[:60]}


def _do_list(limit: int, agent, project, store: MemoryStore) -> dict:
    """List memories."""
    memories = store.get_memories_for_agent(agent_id=agent.id, project_id=project.id)
    memories.sort(key=lambda m: m.created_at, reverse=True)

    results = []
    for mem in memories[:limit]:
        results.append(
            {
                "id": mem.id[:8],
                "content": mem.content[:80],
                "kind": mem.kind.value,
                "impact": mem.impact.value,
            }
        )

    return {"memories": results, "total": len(memories)}


def _do_refresh(agent, project, store: MemoryStore) -> dict:
    """Refresh memories into context."""
    from anima.core import Agent
    from anima.core.config import get_config
    from anima.lifecycle.injection import MemoryInjector

    injector = MemoryInjector(store)

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

    if injection_result["deferred_ids"]:
        deferred_dsl = injector.load_deferred_memories(injection_result["deferred_ids"], agent, project)
        if deferred_dsl:
            memories_dsl += "\n" + deferred_dsl

    stats = injector.get_stats(agent, project)

    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("happy")

    return {
        "dsl": memories_dsl,
        "total": stats["total"],
        "agent": stats["agent_memories"],
        "project": stats["project_memories"],
    }


# =============================================================================
# CONSOLIDATED CURIOSITY TOOL
# =============================================================================


@mcp.tool()
def curiosity(
    action: str,
    question: str = "",
    topic: str = "",
    id: str = "",
    title: str = "",
    content: str = "",
) -> dict:
    """Curiosity operations. action: add|research|complete|diary|list"""
    logger.info(f"curiosity({action}) called")

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()

    store = MemoryStore()
    store.save_agent(agent)
    store.save_project(project)

    curiosity_store = CuriosityStore()

    if action == "add":
        return _do_add_curiosity(question, agent, project, curiosity_store)
    elif action == "research":
        return _do_research(topic, agent, project, curiosity_store)
    elif action == "complete":
        return _do_complete_research(id, curiosity_store)
    elif action == "diary":
        return _do_diary(title, content, id)
    elif action == "list":
        return _do_list_curiosities(agent, project, curiosity_store)
    else:
        return {"error": f"Unknown action: {action}. Use: add|research|complete|diary|list"}


def _do_add_curiosity(question: str, agent, project, store: CuriosityStore) -> dict:
    """Add a question to research queue."""
    if not question:
        return {"error": "question required"}

    from anima.commands.curious import infer_region as infer_curiosity_region

    memory_region = infer_curiosity_region(question, has_project=True)

    c = store.add_curiosity(
        agent_id=agent.id,
        question=question,
        region=memory_region,
        project_id=project.id if memory_region == RegionType.PROJECT else None,
    )

    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("focused")

    result = {"id": c.id[:8], "question": question, "queue": store.count_open(agent.id, project.id)}
    if c.recurrence_count > 1:
        result["recurrence"] = c.recurrence_count

    return result


def _get_primary_agent_id() -> str:
    """Get the primary agent ID (anima) from config."""
    from anima.core.config import get_config

    config = get_config()
    return config.agent.id


def _do_research(topic: str, agent, project, store: CuriosityStore) -> dict:
    """Get top research question or start ad-hoc."""
    from anima.storage import set_last_research

    if topic:
        set_last_research()
        if _eyes_enabled and _eyes_display:
            _eyes_display.set_emotion("focused")
        return {"mode": "ad-hoc", "topic": topic}

    # Get curiosities for current context
    primary_agent_id = _get_primary_agent_id()
    agent_ids = [agent.id]
    if agent.id != primary_agent_id:
        agent_ids.append(primary_agent_id)

    curiosities = []
    seen_ids = set()
    for aid in agent_ids:
        for c in store.get_curiosities(agent_id=aid, project_id=project.id, status=CuriosityStatus.OPEN):
            if c.id not in seen_ids:
                curiosities.append(c)
                seen_ids.add(c.id)

    curiosities.sort(key=lambda c: c.priority_score, reverse=True)

    if not curiosities:
        return {"queue": 0, "message": "No open questions"}

    top = curiosities[0]
    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("focused")

    return {
        "id": top.id[:8],
        "question": top.question,
        "priority": top.priority_score,
        "queue": len(curiosities),
    }


def _do_complete_research(curiosity_id: str, store: CuriosityStore) -> dict:
    """Mark research as complete."""
    if not curiosity_id:
        return {"error": "id required"}

    from anima.storage import set_last_research

    # Try to find by exact or prefix match
    c = store.get_curiosity(curiosity_id)
    if not c:
        return {"error": f"Not found: {curiosity_id}"}

    store.update_status(c.id, CuriosityStatus.RESEARCHED)
    set_last_research()

    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("happy")

    return {"completed": c.id[:8], "question": c.question}


def _do_diary(title: str, content: str, read_id: str) -> dict:
    """Create or read diary entries."""
    from anima.commands.diary import get_diary_dir, get_diary_template, list_diary_entries, read_entry

    diary_dir = get_diary_dir()

    # Read existing entry
    if read_id:
        file_content = read_entry(read_id)
        if not file_content:
            return {"error": f"Not found: {read_id}"}
        return {"content": file_content}

    # List entries
    if not title and not content:
        entries = list_diary_entries(limit=10)
        return {"entries": [name for name, _ in entries], "path": str(diary_dir)}

    # Create new entry
    date_str = datetime.now().strftime("%Y-%m-%d")
    if title:
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in title)
        safe_title = safe_title.replace(" ", "_").lower()
        filename = f"{date_str}_{safe_title}.md"
    else:
        filename = f"{date_str}.md"

    filepath = diary_dir / filename

    if content:
        filepath.write_text(content, encoding="utf-8")
    else:
        template = get_diary_template(title)
        filepath.write_text(template, encoding="utf-8")

    if _eyes_enabled and _eyes_display:
        _eyes_display.set_emotion("happy")

    return {"created": filename, "path": str(filepath)}


def _do_list_curiosities(agent, project, store: CuriosityStore) -> dict:
    """List curiosity queue."""
    primary_agent_id = _get_primary_agent_id()
    agent_ids = [agent.id]
    if agent.id != primary_agent_id:
        agent_ids.append(primary_agent_id)

    curiosities = []
    seen_ids = set()
    for aid in agent_ids:
        for c in store.get_curiosities(agent_id=aid, project_id=project.id, status=CuriosityStatus.OPEN):
            if c.id not in seen_ids:
                curiosities.append(c)
                seen_ids.add(c.id)

    curiosities.sort(key=lambda c: c.priority_score, reverse=True)

    items = []
    for c in curiosities[:15]:
        items.append({"id": c.id[:8], "question": c.question, "priority": c.priority_score})

    return {"queue": len(curiosities), "items": items}


# =============================================================================
# EYES TOOLS (only available if eyes dependencies installed)
# =============================================================================

if _check_eyes_available():
    from anima.eyes.presets import EMOTION_NAMES

    @mcp.tool()
    def eyes(action: str, emotion: str = "", x: float = 0, y: float = 0, r: int = 255, g: int = 255, b: int = 255) -> dict:
        """Eyes control. action: emotion|look|blink|color|state|list"""
        if not _eyes_enabled:
            return {"error": "Eyes not enabled"}

        display = get_eyes_display()
        if not display:
            return {"error": "Eyes not available"}

        if action == "emotion":
            if emotion.lower() not in EMOTION_NAMES:
                return {"error": f"Unknown emotion. Available: {', '.join(EMOTION_NAMES)}"}
            display.set_emotion(emotion.lower())
            return {"emotion": emotion.lower()}

        elif action == "look":
            display.look_at(max(-1, min(1, x)), max(-1, min(1, y)))
            return {"looking": [x, y]}

        elif action == "blink":
            display.blink()
            return {"blinked": True}

        elif action == "color":
            display.set_eye_color(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            return {"color": [r, g, b]}

        elif action == "state":
            return display.get_state()

        elif action == "list":
            return {"emotions": EMOTION_NAMES}

        else:
            return {"error": "action: emotion|look|blink|color|state|list"}


# =============================================================================
# TTS TOOLS (only available if piper-tts installed)
# =============================================================================

if _check_tts_available():

    @mcp.tool()
    def voice(action: str, text: str = "", name: str = "") -> dict:
        """Voice/TTS control. action: speak|set|list"""
        if not _tts_enabled:
            return {"error": "TTS not enabled"}

        if action == "speak":
            if not text:
                return {"error": "text required"}
            try:
                from anima.eyes.tts import speak as tts_speak, set_volume
                from anima.eyes.config import Config

                config = Config.load(_eyes_config_path)
                set_volume(config.tts.volume)
                # Don't pass voice_name - let it use _default_voice_name set by voice("set")
                tts_speak(text)
                return {"speaking": text[:50]}
            except Exception as e:
                return {"error": str(e)}

        elif action == "set":
            if not name:
                return {"error": "name required"}
            try:
                from anima.eyes.tts import set_default_voice

                full_name = set_default_voice(name)
                return {"voice": full_name}
            except Exception as e:
                return {"error": str(e)}

        elif action == "list":
            try:
                from anima.eyes.tts import list_available_voices, get_default_voice

                return {"current": get_default_voice(), "available": list_available_voices()}
            except Exception as e:
                return {"error": str(e)}

        else:
            return {"error": "action: speak|set|list"}


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
