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

# Global state for eyes client and TTS
_eyes_client = None
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

    if _eyes_enabled:
        if memory_impact in (ImpactLevel.HIGH, ImpactLevel.CRITICAL):
            _set_eyes_emotion("happy")

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

    if _eyes_enabled:
        _set_eyes_emotion("focused")

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
        if _eyes_enabled:
            _set_eyes_emotion("focused")
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

    if _eyes_enabled:
        _set_eyes_emotion("happy")

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

        client = get_eyes_client()
        if not client:
            return {"error": "Eyes not available"}

        if action == "emotion":
            if emotion.lower() not in EMOTION_NAMES:
                return {"error": f"Unknown emotion. Available: {', '.join(EMOTION_NAMES)}"}

            emo = emotion.lower()
            result = client.set_emotion(emo)

            # Synchronized color: set eye color AND light to match emotion
            if emo in EMOTION_COLORS:
                er, eg, eb = EMOTION_COLORS[emo]
                client.set_eye_color(er, eg, eb)
                result["eye_color"] = [er, eg, eb]

                # Also set USB light if available
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

        elif action == "color":
            return client.set_eye_color(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))

        elif action == "state":
            return client.get_state()

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
                import os
                import threading

                logger.info(f"Voice speak: text='{text[:30]}...', voice={name or 'default'}")
                logger.debug(f"OPENBLAS_NUM_THREADS={os.environ.get('OPENBLAS_NUM_THREADS', 'not set')}")

                from anima.eyes.tts import speak as tts_speak, set_volume
                from anima.eyes.config import Config

                config = Config.load(_eyes_config_path)
                set_volume(config.tts.volume)

                # Run in separate thread to avoid blocking async event loop
                # Use daemon=False so thread survives and completes synthesis
                # Use mcp_safe=True for numpy-only Joshua (avoids scipy hang)
                def _do_speak():
                    try:
                        tts_speak(text, blocking=True, voice_name=name if name else None, mcp_safe=True)
                    except Exception as e:
                        logger.error(f"TTS thread error: {e}")

                thread = threading.Thread(target=_do_speak, daemon=False)
                thread.start()
                # Don't wait for completion - return immediately
                return {"speaking": text[:50]}
            except Exception as e:
                logger.error(f"Voice speak error: {e}")
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

        elif action == "test":
            # Test audio playback methods in MCP context
            import io
            import wave
            import struct
            import math
            import os
            import time

            # Set the env var NOW before any scipy import
            os.environ["OPENBLAS_NUM_THREADS"] = "1"

            results = {"env_before": "was not set, now set to 1"}

            # Test scipy import
            try:
                start = time.time()
                results["scipy"] = f"OK ({time.time() - start:.2f}s)"
            except Exception as e:
                results["scipy"] = f"FAILED: {e}"

            # Generate beep
            def gen_beep():
                buf = io.BytesIO()
                with wave.open(buf, "wb") as w:
                    w.setnchannels(1)
                    w.setsampwidth(2)
                    w.setframerate(22050)
                    for i in range(int(22050 * 0.5)):
                        v = int(32767 * 0.5 * math.sin(2 * math.pi * 440 * i / 22050))
                        w.writeframes(struct.pack("<h", v))
                return buf.getvalue()

            # Test pygame
            try:
                import pygame

                pygame.mixer.init(frequency=22050, size=-16, channels=1)
                sound = pygame.mixer.Sound(buffer=gen_beep())
                sound.play()
                pygame.time.wait(600)
                results["pygame"] = "OK"
            except Exception as e:
                results["pygame"] = f"FAILED: {e}"

            # Test PowerShell
            try:
                import tempfile

                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                    f.write(gen_beep())
                    tmp = f.name
                ps = f'$p = New-Object System.Media.SoundPlayer("{tmp}"); $p.PlaySync(); Remove-Item "{tmp}" -EA 0'
                import subprocess

                r = subprocess.run(["powershell", "-Command", ps], capture_output=True, creationflags=0x08000000, timeout=5)
                results["powershell"] = f"OK (rc={r.returncode})"
            except Exception as e:
                results["powershell"] = f"FAILED: {e}"

            return results

        else:
            return {"error": "action: speak|set|list|test"}


# =============================================================================
# LIGHT TOOLS (i-Buddy USB light)
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


if _check_light_available():
    from anima.light.ibuddy import COLOR_MAP

    @mcp.tool()
    def light(action: str, color: str = "", r: int = 0, g: int = 0, b: int = 0, heart: bool = False) -> dict:
        """USB light control. action: color|rgb|off|list"""
        if not _light_enabled:
            return {"error": "Light not enabled (use --light flag)"}

        buddy = _get_ibuddy()
        if not buddy:
            return {"error": "i-Buddy not connected"}

        if action == "color":
            if not color:
                return {"error": "color name required (red, green, blue, yellow, cyan, magenta, white, off)"}
            if buddy.set_color_by_name(color, heart=heart):
                return {"status": "ok", "color": color, "heart": heart}
            return {"error": f"Unknown color: {color}. Available: {list(COLOR_MAP.keys())}"}

        elif action == "rgb":
            if buddy.set_rgb(r, g, b, heart=heart):
                return {"status": "ok", "r": r, "g": g, "b": b, "heart": heart}
            return {"error": "Failed to set RGB"}

        elif action == "off":
            if buddy.off():
                return {"status": "ok", "color": "off"}
            return {"error": "Failed to turn off"}

        elif action == "list":
            return {
                "colors": list(COLOR_MAP.keys()),
                "connected": buddy.connected,
                "device_count": buddy.device_count,
            }

        else:
            return {"error": "action: color|rgb|off|list"}


def run_server(
    eyes_enabled: bool = False,
    tts_enabled: bool = False,
    light_enabled: bool = False,
    eyes_config_path: str | None = None,
):
    """Run the MCP server.

    Args:
        eyes_enabled: Whether to enable eyes (visual expression)
        tts_enabled: Whether to enable TTS (text-to-speech)
        light_enabled: Whether to enable i-Buddy USB light
        eyes_config_path: Path to eyes config file
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

    logger.info("Starting MCP server...")
    mcp.run()
    logger.info("MCP server exited")


if __name__ == "__main__":
    run_server()
