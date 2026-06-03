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
from datetime import datetime, UTC
from pathlib import Path
from typing import Literal

from loguru import logger
from mcp.server.fastmcp import FastMCP

from anima.core import (
    Agent,
    Memory,
    Project,
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
from anima.storage import CuriosityStore, CuriosityStatus
from anima.storage.dissonance import DissonanceStore
from anima.utils.spaceship import detect_spaceship

# Configure loguru to write to file (stderr is used by MCP protocol)
logger.remove()
logger.add(
    str(Path.home() / ".anima" / "mcp_server.log"),
    rotation="1 MB",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}",
)

logger.info("=== Anima MCP Server module loaded ===")

# Global state for eyes client and TTS
_eyes_client = None
_eyes_config_path: str | None = None
_eyes_enabled = False
_tts_enabled = False


def _check_eyes_available() -> bool:
    """Check if eyes dependencies (pygame) are available."""
    try:
        import pygame  # noqa: F401

        return True
    except ImportError:
        return False


def _check_tts_available() -> bool:
    """Check if TTS dependencies (piper) are available."""
    try:
        from piper.voice import PiperVoice  # noqa: F401

        return True
    except ImportError:
        return False


def _set_eyes_emotion(emotion: str) -> None:
    """Helper to set emotion on client."""
    if _eyes_client is not None:
        _eyes_client.set_emotion(emotion)


def _spawn_windowless_win32(cmd: list[str]) -> None:
    """Spawn a Python subprocess on Windows without any console window."""
    import subprocess
    import tempfile

    # Build the command string for VBScript, escaping double quotes
    cmd_str = " ".join(f'"""{c}"""' if " " in c else c for c in cmd)
    vbs_content = f'CreateObject("WScript.Shell").Run "{cmd_str}", 0, False\n'

    vbs_path = Path(tempfile.gettempdir()) / "anima_eyes_launch.vbs"
    vbs_path.write_text(vbs_content, encoding="utf-8")

    try:
        subprocess.Popen(
            ["wscript.exe", str(vbs_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )
    except Exception:
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(
            cmd,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
        )


def _auto_start_eyes_daemon() -> bool:
    """Auto-start the eyes daemon if not running."""
    import sys
    import time

    try:
        cmd = [sys.executable, "-m", "anima", "eyes-daemon", "start", "--foreground"]

        if sys.platform == "win32":
            _spawn_windowless_win32(cmd)
        else:
            import subprocess

            subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )

        # Wait for daemon to start
        from anima.eyes.daemon import is_daemon_running

        for _ in range(50):  # Wait up to 5 seconds
            time.sleep(0.1)
            if is_daemon_running():
                logger.info("Eyes daemon auto-started successfully")
                return True

        logger.warning("Eyes daemon did not start in time")
        return False

    except Exception as e:
        logger.warning(f"Failed to auto-start eyes daemon: {e}")
        return False


def get_eyes_client():
    """Get or create the eyes daemon client."""
    global _eyes_client

    if not _eyes_enabled:
        return None

    if _eyes_client is not None:
        return _eyes_client

    try:
        from anima.eyes.daemon import is_daemon_running

        # Auto-start daemon if not running
        if not is_daemon_running():
            logger.info("Eyes daemon not running, auto-starting...")
            if not _auto_start_eyes_daemon():
                return None

        # Connect to daemon
        from anima.eyes.client import EyesDaemonClient

        logger.info("Connecting to eyes daemon...")
        _eyes_client = EyesDaemonClient()
        if _eyes_client.connect():
            logger.info("Connected to eyes daemon")
            return _eyes_client

        logger.warning("Could not connect to eyes daemon")
        _eyes_client = None
        return None

    except Exception as e:
        logger.warning(f"Could not start eyes: {e}")
        return None


@asynccontextmanager
async def lifespan(server):
    """Initialize resources when server starts, cleanup on shutdown."""
    logger.info("MCP server lifespan starting")

    # Connect to eyes daemon if enabled
    if _eyes_enabled:
        client = get_eyes_client()
        if client:
            logger.info("Eyes daemon client ready")

            # Optionally speak greeting
            try:
                from anima.eyes.config import Config
                from anima.eyes.tts import speak_greeting, set_volume
                import time

                config = Config.load(_eyes_config_path)
                if config.tts.enabled and config.tts.speak_on_startup:
                    time.sleep(0.5)
                    client.set_emotion("happy")
                    set_volume(config.tts.volume)
                    speak_greeting(voice_name=config.tts.voice)
            except Exception as e:
                logger.warning(f"Could not speak greeting: {e}")

    try:
        yield
    finally:
        logger.info("MCP server shutting down")
        if _eyes_client is not None:
            _eyes_client.disconnect()
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
    action: Literal["remember", "recall", "forget", "list", "refresh"],
    text: str = "",
    query: str = "",
    memory_id: str = "",
    limit: int = 10,
) -> dict:
    """
    Long-term memory operations.

    Actions:
    - remember: Save a memory (requires: text)
    - recall: Search memories (requires: query or text; optional: limit)
    - forget: Delete a memory (requires: memory_id)
    - list: List all memories (optional: limit)
    - refresh: Re-inject memories into current context
    """
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
        return _do_forget(memory_id, agent, store)
    elif action == "list":
        return _do_list(limit, agent, project, store)
    elif action == "refresh":
        return _do_refresh(agent, project, store)
    else:
        return {"error": f"Unknown action: {action}"}


def _do_remember(text: str, agent: Agent, project: Project, store: MemoryStore) -> dict:
    """Save a memory."""
    if not text:
        return {"error": "text required for remember"}

    now = datetime.now(UTC)
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

    if should_sign(agent) and agent.signing_key:
        mem.signature = sign_memory(mem, agent.signing_key)

    ensure_token_count(mem)
    store.save_memory(mem)

    # Generate embedding and find links
    semantic_links = 0
    candidates: list = []
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

    if _eyes_enabled:
        if memory_impact in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
            _set_eyes_emotion("happy")

    result: dict = {
        "id": mem.id[:8],
        "kind": memory_kind.value,
        "impact": memory_impact.value,
        "links": semantic_links,
    }

    # Check for potential supersession/thread candidates
    # Only suggest if we found high-similarity matches during link creation
    if candidates:
        top_match = candidates[0]
        if top_match.similarity >= 0.70:
            # Get the actual memory content for context
            related_mem = store.get_memory(top_match.memory_id)
            if related_mem and not related_mem.is_superseded():
                result["related_memory"] = {
                    "id": top_match.memory_id[:8],
                    "similarity": round(top_match.similarity, 2),
                    "content_preview": related_mem.content[:100].replace("\n", " "),
                    "suggestion": ("HIGH_CONFIDENCE" if top_match.similarity >= 0.85 else "REVIEW_SUGGESTED"),
                }

    return result


def _do_recall(query: str, limit: int, agent: Agent, project: Project, store: MemoryStore) -> dict:
    """Search memories."""
    if not query:
        return {"error": "query required for recall"}

    if _eyes_enabled:
        _set_eyes_emotion("focused")

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

    if _eyes_enabled:
        _set_eyes_emotion("normal")

    return {"results": results[:limit], "count": len(results)}


def _do_forget(memory_id: str, agent: Agent, store: MemoryStore) -> dict:
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
    now = datetime.now(UTC)

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


def _do_list(limit: int, agent: Agent, project: Project, store: MemoryStore) -> dict:
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


def _do_refresh(agent: Agent, project: Project, store: MemoryStore) -> dict:
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

    if _eyes_enabled:
        _set_eyes_emotion("happy")

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
    action: Literal["add", "research", "complete", "diary", "list"],
    question: str = "",
    topic: str = "",
    curiosity_id: str = "",
    title: str = "",
    content: str = "",
) -> dict:
    """
    Curiosity queue for autonomous learning.

    Actions:
    - add: Add a question to the research queue (requires: question)
    - research: Get the top question to explore (optional: topic filter)
    - complete: Mark a question as researched (requires: curiosity_id)
    - diary: Create a research diary entry (requires: title, content)
    - list: List pending questions in the queue
    """
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
        return _do_complete_research(curiosity_id, curiosity_store)
    elif action == "diary":
        return _do_diary(title, content, curiosity_id)
    elif action == "list":
        return _do_list_curiosities(agent, project, curiosity_store)
    else:
        return {"error": f"Unknown action: {action}. Use: add|research|complete|diary|list"}


def _do_add_curiosity(question: str, agent: Agent, project: Project, store: CuriosityStore) -> dict:
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

    if _eyes_enabled:
        _set_eyes_emotion("focused")

    result = {
        "id": c.id[:8],
        "question": question,
        "queue": store.count_open(agent.id, project.id),
    }
    if c.recurrence_count > 1:
        result["recurrence"] = c.recurrence_count

    return result


def _get_primary_agent_id() -> str:
    """Get the primary agent ID (anima) from config."""
    from anima.core.config import get_config

    config = get_config()
    return config.agent.id


def _get_curiosities_for_context(agent: Agent, project: Project, store: CuriosityStore) -> list:
    """Get deduplicated curiosities for current agent + primary agent context."""
    primary_agent_id = _get_primary_agent_id()
    agent_ids = [agent.id]
    if agent.id != primary_agent_id:
        agent_ids.append(primary_agent_id)

    curiosities = []
    seen_ids: set[str] = set()
    for aid in agent_ids:
        for c in store.get_curiosities(agent_id=aid, project_id=project.id, status=CuriosityStatus.OPEN):
            if c.id not in seen_ids:
                curiosities.append(c)
                seen_ids.add(c.id)

    curiosities.sort(key=lambda c: c.priority_score, reverse=True)
    return curiosities


def _do_research(topic: str, agent: Agent, project: Project, store: CuriosityStore) -> dict:
    """Get top research question or start ad-hoc."""
    from anima.storage import set_last_research

    if topic:
        set_last_research()
        if _eyes_enabled:
            _set_eyes_emotion("focused")
        return {"mode": "ad-hoc", "topic": topic}

    curiosities = _get_curiosities_for_context(agent, project, store)

    if not curiosities:
        return {"queue": 0, "message": "No open questions"}

    top = curiosities[0]
    if _eyes_enabled:
        _set_eyes_emotion("focused")

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

    if _eyes_enabled:
        _set_eyes_emotion("happy")

    return {"completed": c.id[:8], "question": c.question}


def _do_diary(title: str, content: str, read_id: str) -> dict:
    """Create or read diary entries."""
    from anima.commands.diary import (
        get_diary_dir,
        get_diary_template,
        list_diary_entries,
        read_entry,
    )

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
    date_str = datetime.now(UTC).strftime("%Y-%m-%d")
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

    if _eyes_enabled:
        _set_eyes_emotion("happy")

    return {"created": filename, "path": str(filepath)}


def _do_list_curiosities(agent: Agent, project: Project, store: CuriosityStore) -> dict:
    """List curiosity queue."""
    curiosities = _get_curiosities_for_context(agent, project, store)

    items = []
    for c in curiosities[:15]:
        items.append({"id": c.id[:8], "question": c.question, "priority": c.priority_score})

    return {"queue": len(curiosities), "items": items}


# =============================================================================
# DREAM TOOL
# =============================================================================


@mcp.tool()
def dream(
    action: Literal["run", "status", "wake"],
    stage: str = "all",
    lookback_days: int = 7,
) -> dict:
    """
    Dream processing for memory consolidation.

    Actions:
    - run: Run dream stages (n2, n3, rem, or all)
    - status: Check if there's a pending dream journal to process
    - wake: Process the most recent dream journal and save insights to memory
    """
    logger.info(f"dream({action}) called with stage={stage}")

    if action == "run":
        return _do_dream_run(stage, lookback_days)
    elif action == "status":
        return _do_dream_status()
    elif action == "wake":
        return _do_dream_wake()
    else:
        return {"error": f"Unknown action: {action}"}


def _do_dream_run(stage: str, lookback_days: int) -> dict:
    """Run dream processing stages."""
    from anima.commands.dream import run as run_dream

    valid_stages = ["n2", "n3", "rem", "all"]
    if stage.lower() not in valid_stages:
        return {"error": f"Invalid stage: {stage}. Use: {', '.join(valid_stages)}"}

    # Build args for dream command
    args = ["--stage", stage.lower(), "--lookback-days", str(lookback_days)]

    try:
        # Capture the journal path by running dream
        result = run_dream(args)
        if result == 0:
            return {"status": "completed", "stage": stage}
        else:
            return {"status": "error", "code": result}
    except Exception as e:
        logger.error(f"Dream run error: {e}")
        return {"error": str(e)}


def _do_dream_status() -> dict:
    """Check for pending dream journals."""
    from anima.commands.dream_wake import find_latest_dream_journal

    journal = find_latest_dream_journal()

    if not journal:
        return {"pending": False, "message": "No dream journals found"}

    return {
        "pending": True,
        "latest": journal.name,
        "path": str(journal),
    }


def _do_dream_wake() -> dict:
    """Process dream journal and save insights."""
    from anima.commands.dream_wake import run as run_wake

    try:
        result = run_wake([])
        if result == 0:
            return {"status": "completed", "message": "Dream insights saved to memory"}
        else:
            return {"status": "error", "code": result}
    except Exception as e:
        logger.error(f"Dream wake error: {e}")
        return {"error": str(e)}


# =============================================================================
# DISSONANCE TOOL
# =============================================================================


@mcp.tool()
def dissonance(
    action: Literal["list", "show", "resolve", "dismiss", "migrate"],
    dissonance_id: str = "",
    explanation: str = "",
) -> dict:
    """
    Cognitive dissonance management.

    Actions:
    - list: Show all open dissonances
    - show: Show details of a specific dissonance (requires: dissonance_id)
    - resolve: Mark as resolved with explanation (requires: dissonance_id, explanation)
    - dismiss: Dismiss as not a real contradiction (requires: dissonance_id)
    - migrate: Accept the suggested scope migration (requires: dissonance_id)
    """
    logger.info(f"dissonance({action}) called")

    store = DissonanceStore()

    if action == "list":
        return _do_dissonance_list(store)
    elif action == "show":
        return _do_dissonance_show(dissonance_id, store)
    elif action == "resolve":
        return _do_dissonance_resolve(dissonance_id, explanation, store)
    elif action == "dismiss":
        return _do_dissonance_dismiss(dissonance_id, store)
    elif action == "migrate":
        return _do_dissonance_migrate(dissonance_id, store)
    else:
        return {"error": f"Unknown action: {action}"}


def _do_dissonance_list(store: DissonanceStore) -> dict:
    """List open dissonances."""
    from anima.core import AgentResolver

    resolver = AgentResolver()
    agent = resolver.resolve()
    dissonances = store.get_open_dissonances(agent.id)

    items = []
    for d in dissonances[:20]:
        items.append(
            {
                "id": d.id[:8],
                "type": d.dissonance_type.value if hasattr(d.dissonance_type, "value") else str(d.dissonance_type),
                "issue": d.description[:100] if d.description else "",
                "detected": d.detected_at.strftime("%Y-%m-%d") if d.detected_at else "",
            }
        )

    return {"count": len(dissonances), "items": items}


def _do_dissonance_show(dissonance_id: str, store: DissonanceStore) -> dict:
    """Show details of a dissonance."""
    if not dissonance_id:
        return {"error": "id required"}

    d = store.get_dissonance(dissonance_id)
    if not d:
        return {"error": f"Not found: {dissonance_id}"}

    result: dict = {
        "id": d.id[:8],
        "type": d.dissonance_type.value if hasattr(d.dissonance_type, "value") else str(d.dissonance_type),
        "status": d.status.value,
        "memory_id_a": d.memory_id_a[:8] if d.memory_id_a else None,
        "memory_id_b": d.memory_id_b[:8] if d.memory_id_b else None,
        "description": d.description,
    }

    if d.suggested_region:
        result["suggested_region"] = d.suggested_region
    if d.suggested_project_id:
        result["suggested_project_id"] = d.suggested_project_id

    # Load memory content if available
    if d.memory_id_a:
        mem_store = MemoryStore()
        mem = mem_store.get_memory(d.memory_id_a)
        if mem:
            result["memory_content"] = mem.content[:500]
            result["memory_kind"] = mem.kind.value

    return result


def _do_dissonance_resolve(dissonance_id: str, explanation: str, store: DissonanceStore) -> dict:
    """Resolve a dissonance with explanation."""
    if not dissonance_id:
        return {"error": "id required"}
    if not explanation:
        return {"error": "explanation required"}

    d = store.get_dissonance(dissonance_id)
    if not d:
        return {"error": f"Not found: {dissonance_id}"}

    store.resolve_dissonance(d.id, resolution=explanation)

    return {"resolved": d.id[:8], "explanation": explanation[:100]}


def _do_dissonance_dismiss(dissonance_id: str, store: DissonanceStore) -> dict:
    """Dismiss a dissonance as not a real contradiction."""
    if not dissonance_id:
        return {"error": "id required"}

    d = store.get_dissonance(dissonance_id)
    if not d:
        return {"error": f"Not found: {dissonance_id}"}

    store.dismiss_dissonance(d.id)

    return {"dismissed": d.id[:8]}


def _do_dissonance_migrate(dissonance_id: str, store: DissonanceStore) -> dict:
    """Accept the suggested scope migration."""
    if not dissonance_id:
        return {"error": "id required"}

    d = store.get_dissonance(dissonance_id)
    if not d:
        return {"error": f"Not found: {dissonance_id}"}

    if not d.suggested_region:
        return {"error": "No suggested migration for this dissonance"}

    # Perform the migration
    mem_store = MemoryStore()
    mem = mem_store.get_memory(d.memory_id_a)
    if not mem:
        return {"error": f"Memory not found: {d.memory_id_a}"}

    # Update memory region
    new_region = RegionType.AGENT if d.suggested_region == "AGENT" else RegionType.PROJECT
    new_project_id = d.suggested_project_id if new_region == RegionType.PROJECT else None

    mem_store.migrate_memory_region(d.memory_id_a, new_region, new_project_id)
    store.resolve_dissonance(d.id, resolution=f"Migrated to {d.suggested_region}")

    return {
        "migrated": d.id[:8],
        "memory": d.memory_id_a[:8],
        "new_region": d.suggested_region,
        "new_project": d.suggested_project_id,
    }


# =============================================================================
# EMOTION COLOR MAPPING - Unified embodiment colors
# =============================================================================

# Maps emotions to RGB tuples for synchronized eyes + light colors
EMOTION_COLORS: dict[str, tuple[int, int, int]] = {
    "normal": (0, 255, 255),  # cyan - neutral/default
    "happy": (0, 255, 0),  # green - positive
    "glee": (255, 255, 0),  # yellow - bright joy
    "excited": (255, 200, 0),  # gold - enthusiasm
    "awe": (255, 0, 255),  # magenta - wonder
    "surprised": (255, 255, 0),  # yellow - alert
    "focused": (0, 200, 255),  # cyan-blue - concentration
    "suspicious": (255, 0, 255),  # magenta - caution
    "skeptic": (255, 0, 255),  # magenta - doubt
    "annoyed": (255, 100, 0),  # orange - mild frustration
    "frustrated": (255, 50, 0),  # red-orange - frustration
    "angry": (255, 0, 0),  # red - anger
    "furious": (255, 0, 0),  # red - intense anger
    "sad": (0, 100, 255),  # blue - melancholy
    "worried": (255, 200, 0),  # amber - concern
    "scared": (0, 150, 255),  # light blue - fear
    "sleepy": (100, 100, 200),  # soft blue - drowsy
    "unimpressed": (150, 150, 150),  # gray-ish - meh
    "squint": (0, 200, 255),  # cyan - peering
}


# NOTE: Legacy eyes/voice/light tools removed - use consolidated 'body' tool instead


# =============================================================================
# LIGHT HELPERS (i-Buddy USB light) - used by body tool
# =============================================================================

_light_enabled = False
_ibuddy_instance = None


def _check_light_available() -> bool:
    """Check if hidapi is available for light control."""
    try:
        import hid  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def _get_ibuddy():
    """Get or create the i-Buddy singleton."""
    global _ibuddy_instance
    if _ibuddy_instance is None:
        from anima.light.ibuddy import IBuddy

        _ibuddy_instance = IBuddy()
        if not _ibuddy_instance.open():
            _ibuddy_instance = None
    return _ibuddy_instance


# =============================================================================
# CONSOLIDATED DOCTOR TOOL (diagnostics: trust, stats, graph)
# =============================================================================


@mcp.tool()
def doctor(
    action: Literal["trust", "trust-eval", "trust-set", "trust-reset", "stats", "graph"],
    message: str = "",
    value: float = 0.0,
    memory_id: str = "",
) -> dict:
    """
    System diagnostics and trust management.

    Actions:
    - trust: Show current trust level and score
    - trust-eval: Evaluate a user message and update trust score (requires: message)
    - trust-set: Set trust to specific value (requires: value, range 0.0-1.0)
    - trust-reset: Reset trust to default (0.5)
    - stats: Show memory statistics
    - graph: Show memory graph info (optional: memory_id for specific memory)
    """
    logger.info(f"doctor({action}) called")

    if action == "trust":
        return _do_doctor_trust_status()
    elif action == "trust-eval":
        return _do_doctor_trust_eval(message)
    elif action == "trust-set":
        return _do_doctor_trust_set(value)
    elif action == "trust-reset":
        return _do_doctor_trust_reset()
    elif action == "stats":
        return _do_doctor_stats()
    elif action == "graph":
        return _do_doctor_graph(memory_id)
    else:
        return {"error": f"Unknown action: {action}. Use: trust|trust-eval|trust-set|trust-reset|stats|graph"}


def _do_doctor_trust_status() -> dict:
    """Show current trust level."""
    from anima.security.cognitive_auth import (
        get_session_trust,
        get_memory_access_filter,
    )

    trust_score = get_session_trust()
    level = trust_score.get_trust_level()
    filters = get_memory_access_filter(trust_score)

    return {
        "score": round(trust_score.score, 3),
        "level": level.value,
        "challenges_issued": trust_score.challenges_issued,
        "challenges_passed": trust_score.challenges_passed,
        "filters": {k: str(v) for k, v in filters.items()},
    }


def _do_doctor_trust_eval(message: str) -> dict:
    """Evaluate a message and update trust."""
    if not message:
        return {"error": "message required for trust-eval action"}

    from anima.security.cognitive_auth import evaluate_and_update_trust

    return evaluate_and_update_trust(message)


def _do_doctor_trust_set(value: float) -> dict:
    """Set trust to specific value."""
    if not 0.0 <= value <= 1.0:
        return {"error": "value must be between 0.0 and 1.0"}

    from anima.security.cognitive_auth import update_trust_score

    trust_score = update_trust_score(absolute=value)
    return {
        "score": round(trust_score.score, 3),
        "level": trust_score.get_trust_level().value,
        "message": f"Trust set to {value:.2f}",
    }


def _do_doctor_trust_reset() -> dict:
    """Reset trust to default."""
    from anima.security.cognitive_auth import reset_session_trust, get_session_trust

    reset_session_trust()
    trust_score = get_session_trust()
    return {
        "score": round(trust_score.score, 3),
        "level": trust_score.get_trust_level().value,
        "message": "Trust reset to 0.5",
    }


def _do_doctor_stats() -> dict:
    """Show memory statistics."""
    from collections import Counter

    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()
    store = MemoryStore()

    memories = store.get_memories_for_agent(agent_id=agent.id, project_id=project.id)

    if not memories:
        return {"total": 0, "message": f"No memories for agent '{agent.name}'"}

    by_region: Counter[str] = Counter()
    by_kind: Counter[str] = Counter()
    by_impact: Counter[str] = Counter()
    superseded = 0
    low_confidence = 0

    for m in memories:
        by_region[m.region.value] += 1
        by_kind[m.kind.value] += 1
        by_impact[m.impact.value] += 1
        if m.superseded_by:
            superseded += 1
        if m.is_low_confidence():
            low_confidence += 1

    return {
        "total": len(memories),
        "agent": agent.name,
        "project": project.name if project else None,
        "by_region": dict(by_region),
        "by_kind": dict(by_kind),
        "by_impact": dict(by_impact),
        "health": {
            "active": len(memories) - superseded,
            "superseded": superseded,
            "low_confidence": low_confidence,
        },
    }


def _do_doctor_graph(memory_id: str) -> dict:
    """Show memory graph info."""
    resolver = AgentResolver()
    agent = resolver.resolve()
    project = resolver.resolve_project()
    store = MemoryStore()

    memories = store.get_memories_for_agent(agent_id=agent.id, project_id=project.id)

    if not memories:
        return {"total": 0, "message": "No memories"}

    # Count links
    total_links = 0
    link_types: dict[str, int] = {}
    for m in memories:
        links = store.get_links_for_memory(m.id)
        for _, _, lt, _ in links:
            total_links += 1
            link_types[lt] = link_types.get(lt, 0) + 1

    # If specific memory requested, show its links
    if memory_id:
        mem = store.get_memory(memory_id)
        if not mem:
            return {"error": f"Memory not found: {memory_id}"}

        links = store.get_links_for_memory(mem.id)
        link_details = []
        for src, tgt, lt, sim in links:
            other_id = tgt if src == mem.id else src
            link_details.append(
                {
                    "target": other_id[:8],
                    "type": lt,
                    "similarity": round(sim, 2) if sim else None,
                }
            )

        return {
            "memory": mem.id[:8],
            "content": mem.content[:100],
            "links": link_details,
            "link_count": len(links),
        }

    # Overall summary
    return {
        "total_memories": len(memories),
        "total_links": total_links // 2,  # Links are bidirectional
        "link_types": link_types,
    }


# =============================================================================
# CONSOLIDATED BODY TOOL (embodiment: eyes, voice, light)
# =============================================================================


@mcp.tool()
def body(
    action: Literal[
        "emotion",
        "look",
        "blink",
        "speak",
        "voice-set",
        "voice-list",
        "light",
        "light-off",
    ],
    emotion: str = "",
    text: str = "",
    voice: str = "",
    color: str = "",
    x: float = 0,
    y: float = 0,
    r: int = 0,
    g: int = 0,
    b: int = 0,
) -> dict:
    """
    Embodiment control for eyes, voice, and light.

    Actions:
    - emotion: Set eye emotion (requires: emotion)
    - look: Set look direction (requires: x, y in range -1 to 1)
    - blink: Trigger blink animation
    - speak: Speak text aloud (requires: text; optional: voice)
    - voice-set: Set default voice (requires: voice)
    - voice-list: List available voices
    - light: Set i-Buddy light color (requires: color name OR r,g,b values)
    - light-off: Turn off i-Buddy light
    """
    logger.info(f"body({action}) called")

    # Route to appropriate subsystem
    if action in ("emotion", "look", "blink"):
        return _do_body_eyes(action, emotion, x, y)
    elif action in ("speak", "voice-set", "voice-list"):
        return _do_body_voice(action, text, voice)
    elif action in ("light", "light-off"):
        return _do_body_light(action, color, r, g, b)
    else:
        return {"error": f"Unknown action: {action}"}


def _do_body_eyes(action: str, emotion: str, x: float, y: float) -> dict:
    """Handle eyes actions."""
    if not _eyes_enabled:
        return {"error": "Eyes not enabled (use --eyes flag)"}

    if not _check_eyes_available():
        return {"error": "pygame not installed"}

    client = get_eyes_client()
    if not client:
        return {"error": "Eyes daemon not available"}

    if action == "emotion":
        from anima.eyes.presets import EMOTION_NAMES

        if not emotion:
            return {"error": "emotion param required", "available": EMOTION_NAMES}

        emo = emotion.lower()
        if emo not in EMOTION_NAMES:
            return {"error": "Unknown emotion", "available": EMOTION_NAMES}

        result = client.set_emotion(emo)

        # Synchronized color
        if emo in EMOTION_COLORS:
            er, eg, eb = EMOTION_COLORS[emo]
            client.set_eye_color(er, eg, eb)
            result["eye_color"] = [er, eg, eb]

            # Also set light if available
            if _light_enabled:
                buddy = _get_ibuddy()
                if buddy:
                    buddy.set_rgb(er, eg, eb)
                    result["light_color"] = [er, eg, eb]

        return result

    elif action == "look":
        return client.look_at(max(-1, min(1, x)), max(-1, min(1, y)))

    elif action == "blink":
        return client.blink()

    return {"error": "Unknown eyes action"}


def _do_body_voice(action: str, text: str, voice: str) -> dict:
    """Handle voice/TTS actions."""
    if not _tts_enabled:
        return {"error": "TTS not enabled (use --tts flag)"}

    if not _check_tts_available():
        return {"error": "piper-tts not installed"}

    if action == "speak":
        if not text:
            return {"error": "text param required"}

        try:
            import threading

            from anima.eyes.tts import speak as tts_speak, set_volume
            from anima.eyes.config import Config

            config = Config.load(_eyes_config_path)
            set_volume(config.tts.volume)

            def _do_speak():
                try:
                    tts_speak(
                        text,
                        blocking=True,
                        voice_name=voice if voice else None,
                        mcp_safe=True,
                    )
                except Exception as e:
                    logger.error(f"TTS thread error: {e}")

            thread = threading.Thread(target=_do_speak, daemon=False)
            thread.start()
            return {"speaking": text[:50], "voice": voice or "default"}
        except Exception as e:
            logger.error(f"Voice speak error: {e}")
            return {"error": str(e)}

    elif action == "voice-set":
        if not voice:
            return {"error": "voice param required"}
        try:
            from anima.eyes.tts import set_default_voice

            full_name = set_default_voice(voice)
            return {"voice": full_name}
        except Exception as e:
            return {"error": str(e)}

    elif action == "voice-list":
        try:
            from anima.eyes.tts import list_available_voices, get_default_voice

            return {
                "current": get_default_voice(),
                "available": list_available_voices(),
            }
        except Exception as e:
            return {"error": str(e)}

    return {"error": "Unknown voice action"}


def _do_body_light(action: str, color: str, r: int, g: int, b: int) -> dict:
    """Handle light actions."""
    if not _light_enabled:
        return {"error": "Light not enabled (use --light flag)"}

    if not _check_light_available():
        return {"error": "hidapi not installed"}

    buddy = _get_ibuddy()
    if not buddy:
        return {"error": "i-Buddy not connected"}

    if action == "light":
        if color:
            from anima.light.ibuddy import COLOR_MAP

            if buddy.set_color_by_name(color):
                return {"status": "ok", "color": color}
            return {
                "error": f"Unknown color: {color}",
                "available": list(COLOR_MAP.keys()),
            }
        elif r or g or b:
            if buddy.set_rgb(r, g, b):
                return {"status": "ok", "r": r, "g": g, "b": b}
            return {"error": "Failed to set RGB"}
        else:
            return {"error": "Provide color name or r,g,b values"}

    elif action == "light-off":
        if buddy.off():
            return {"status": "ok", "color": "off"}
        return {"error": "Failed to turn off"}

    return {"error": "Unknown light action"}


def run_server(
    eyes_enabled: bool = False,
    tts_enabled: bool = False,
    light_enabled: bool = False,
    eyes_config_path: str | None = None,
    http: bool = False,
    host: str = "127.0.0.1",
    port: int = 3737,
):
    """Run the MCP server.

    Args:
        eyes_enabled: Whether to enable eyes (visual expression)
        tts_enabled: Whether to enable TTS (text-to-speech)
        light_enabled: Whether to enable i-Buddy USB light
        eyes_config_path: Path to eyes config file
        http: Serve over streamable-HTTP instead of stdio. Avoids the Windows
            stdio response-delivery hang; the server runs once and all Claude
            Code sessions connect to it by URL.
        host: Bind host for HTTP transport
        port: Bind port for HTTP transport
    """
    global _eyes_enabled, _tts_enabled, _light_enabled, _eyes_config_path
    _eyes_enabled = eyes_enabled and _check_eyes_available()
    _tts_enabled = tts_enabled and _check_tts_available()
    _light_enabled = light_enabled and _check_light_available()
    _eyes_config_path = eyes_config_path

    if _eyes_enabled:
        logger.info("Eyes features enabled (visual expression)")
    else:
        logger.info("Running without eyes (not enabled or pygame not installed)")

    if _tts_enabled:
        logger.info("TTS features enabled (text-to-speech)")
    else:
        logger.info("Running without TTS (not enabled or piper not installed)")

    if _light_enabled:
        logger.info("Light features enabled (i-Buddy USB)")
    else:
        logger.info("Running without light (not enabled or hidapi not installed)")

    if http:
        mcp.settings.host = host
        mcp.settings.port = port
        logger.info(f"Starting MCP server over streamable-HTTP at http://{host}:{port}{mcp.settings.streamable_http_path}")
        mcp.run(transport="streamable-http")
    else:
        logger.info("Starting MCP server (stdio)...")
        mcp.run()
    logger.info("MCP server exited")


if __name__ == "__main__":
    run_server()
