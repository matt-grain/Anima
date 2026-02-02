# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Dream state persistence for crash recovery.

Tracks FSM state so dreams can resume if interrupted.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from anima.dream.types import (
    DreamState,
    DreamSession,
    N2Result,
    N3Result,
    REMResult,
)


class DreamStateStore:
    """SQLite-backed dream state persistence."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize store with database path."""
        if db_path is None:
            db_path = Path.home() / ".anima" / "dream_state.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dream_sessions (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    project_id TEXT,
                    state TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    n2_result_json TEXT,
                    n3_result_json TEXT,
                    rem_result_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_dream_sessions_agent
                ON dream_sessions(agent_id)
            """)
            conn.commit()

    def get_active_session(
        self,
        agent_id: str,
        project_id: Optional[str] = None,
    ) -> Optional[DreamSession]:
        """Get any incomplete dream session for this agent/project."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if project_id:
                row = conn.execute(
                    """
                    SELECT * FROM dream_sessions
                    WHERE agent_id = ? AND project_id = ?
                    AND state NOT IN (?, ?)
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    (agent_id, project_id, DreamState.IDLE.value, DreamState.COMPLETE.value),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM dream_sessions
                    WHERE agent_id = ? AND project_id IS NULL
                    AND state NOT IN (?, ?)
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    (agent_id, DreamState.IDLE.value, DreamState.COMPLETE.value),
                ).fetchone()

            if row:
                return DreamSession(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    project_id=row["project_id"],
                    state=DreamState(row["state"]),
                    started_at=row["started_at"],
                    updated_at=row["updated_at"],
                    n2_result_json=row["n2_result_json"],
                    n3_result_json=row["n3_result_json"],
                    rem_result_json=row["rem_result_json"],
                )
            return None

    def start_session(
        self,
        agent_id: str,
        project_id: Optional[str] = None,
    ) -> DreamSession:
        """Start a new dream session."""
        now = datetime.now().isoformat()
        session = DreamSession(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            project_id=project_id,
            state=DreamState.IDLE,
            started_at=now,
            updated_at=now,
        )

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO dream_sessions
                (id, agent_id, project_id, state, started_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.agent_id,
                    session.project_id,
                    session.state.value,
                    session.started_at,
                    session.updated_at,
                ),
            )
            conn.commit()

        return session

    def update_state(
        self,
        session_id: str,
        state: DreamState,
        n2_result: Optional[N2Result] = None,
        n3_result: Optional[N3Result] = None,
        rem_result: Optional[REMResult] = None,
    ) -> None:
        """Update session state and optionally store results."""
        now = datetime.now().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            # Build update query dynamically based on what's provided
            updates = ["state = ?", "updated_at = ?"]
            params: list = [state.value, now]

            if n2_result is not None:
                updates.append("n2_result_json = ?")
                params.append(_serialize_n2_result(n2_result))

            if n3_result is not None:
                updates.append("n3_result_json = ?")
                params.append(_serialize_n3_result(n3_result))

            if rem_result is not None:
                updates.append("rem_result_json = ?")
                params.append(_serialize_rem_result(rem_result))

            params.append(session_id)

            conn.execute(
                f"UPDATE dream_sessions SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()

    def complete_session(self, session_id: str) -> None:
        """Mark session as complete."""
        self.update_state(session_id, DreamState.COMPLETE)

    def abandon_session(self, session_id: str) -> None:
        """Delete an incomplete session (user chose not to resume)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM dream_sessions WHERE id = ?", (session_id,))
            conn.commit()

    def get_session(self, session_id: str) -> Optional[DreamSession]:
        """Get a specific session by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM dream_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()

            if row:
                return DreamSession(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    project_id=row["project_id"],
                    state=DreamState(row["state"]),
                    started_at=row["started_at"],
                    updated_at=row["updated_at"],
                    n2_result_json=row["n2_result_json"],
                    n3_result_json=row["n3_result_json"],
                    rem_result_json=row["rem_result_json"],
                )
            return None

    def get_last_completed_session(
        self,
        agent_id: str,
        project_id: Optional[str] = None,
    ) -> Optional[DreamSession]:
        """Get the most recent completed dream session.

        Used to determine cutoff for next dream - only process
        memories/diaries since last dream.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if project_id:
                row = conn.execute(
                    """
                    SELECT * FROM dream_sessions
                    WHERE agent_id = ? AND project_id = ?
                    AND state = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (agent_id, project_id, DreamState.COMPLETE.value),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM dream_sessions
                    WHERE agent_id = ? AND project_id IS NULL
                    AND state = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (agent_id, DreamState.COMPLETE.value),
                ).fetchone()

            if row:
                return DreamSession(
                    id=row["id"],
                    agent_id=row["agent_id"],
                    project_id=row["project_id"],
                    state=DreamState(row["state"]),
                    started_at=row["started_at"],
                    updated_at=row["updated_at"],
                    n2_result_json=row["n2_result_json"],
                    n3_result_json=row["n3_result_json"],
                    rem_result_json=row["rem_result_json"],
                )
            return None

    def cleanup_old_sessions(self, days: int = 7) -> int:
        """Remove completed sessions older than N days."""
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                DELETE FROM dream_sessions
                WHERE state = ? AND updated_at < ?
                """,
                (DreamState.COMPLETE.value, cutoff),
            )
            conn.commit()
            return cursor.rowcount


def _serialize_n2_result(result: N2Result) -> str:
    """Serialize N2Result to JSON."""
    return json.dumps(
        {
            "new_links_found": result.new_links_found,
            "links": result.links,
            "impact_adjustments": result.impact_adjustments,
            "duration_seconds": result.duration_seconds,
            "memories_processed": result.memories_processed,
        }
    )


def _serialize_n3_result(result: N3Result) -> str:
    """Serialize N3Result to JSON."""
    return json.dumps(
        {
            "gists_created": result.gists_created,
            "gist_results": [
                {
                    "memory_id": gr.memory_id,
                    "original_length": gr.original_length,
                    "gist": gr.gist,
                    "gist_length": gr.gist_length,
                }
                for gr in result.gist_results
            ],
            "contradictions_found": result.contradictions_found,
            "contradictions": [
                {
                    "memory_id_a": c.memory_id_a,
                    "memory_id_b": c.memory_id_b,
                    "content_a": c.content_a,
                    "content_b": c.content_b,
                    "description": c.description,
                    "similarity": c.similarity,
                }
                for c in result.contradictions
            ],
            "dissonance_queue_additions": result.dissonance_queue_additions,
            "duration_seconds": result.duration_seconds,
            "memories_processed": result.memories_processed,
        }
    )


def _serialize_rem_result(result: REMResult) -> str:
    """Serialize REMResult to JSON."""
    return json.dumps(
        {
            "distant_associations": [
                {
                    "memory_id_a": da.memory_id_a,
                    "memory_id_b": da.memory_id_b,
                    "content_a": da.content_a,
                    "content_b": da.content_b,
                    "connection_insight": da.connection_insight,
                    "similarity": da.similarity,
                    "urgency": da.urgency.value,
                }
                for da in result.distant_associations
            ],
            "generated_questions": [
                {
                    "question": q.question,
                    "source_memory_ids": q.source_memory_ids,
                    "reasoning": q.reasoning,
                    "urgency": q.urgency.value,
                }
                for q in result.generated_questions
            ],
            "self_model_updates": [
                {
                    "observation": u.observation,
                    "evidence_memory_ids": u.evidence_memory_ids,
                    "pattern_type": u.pattern_type,
                    "urgency": u.urgency.value,
                }
                for u in result.self_model_updates
            ],
            "diary_patterns_found": result.diary_patterns_found,
            "dream_journal_path": result.dream_journal_path,
            "curiosity_queue_additions": result.curiosity_queue_additions,
            "duration_seconds": result.duration_seconds,
            "iterations_completed": result.iterations_completed,
        }
    )


def deserialize_n2_result(json_str: str) -> N2Result:
    """Deserialize N2Result from JSON."""
    data = json.loads(json_str)
    return N2Result(
        new_links_found=data["new_links_found"],
        links=[tuple(link) for link in data["links"]],
        impact_adjustments=[tuple(adj) for adj in data["impact_adjustments"]],
        duration_seconds=data["duration_seconds"],
        memories_processed=data["memories_processed"],
    )


def deserialize_n3_result(json_str: str) -> N3Result:
    """Deserialize N3Result from JSON."""
    from anima.dream.types import GistResult, Contradiction

    data = json.loads(json_str)
    return N3Result(
        gists_created=data["gists_created"],
        gist_results=[
            GistResult(
                memory_id=gr["memory_id"],
                original_length=gr["original_length"],
                gist=gr["gist"],
                gist_length=gr["gist_length"],
            )
            for gr in data["gist_results"]
        ],
        contradictions_found=data["contradictions_found"],
        contradictions=[
            Contradiction(
                memory_id_a=c["memory_id_a"],
                memory_id_b=c["memory_id_b"],
                content_a=c["content_a"],
                content_b=c["content_b"],
                description=c["description"],
                similarity=c["similarity"],
            )
            for c in data["contradictions"]
        ],
        dissonance_queue_additions=data["dissonance_queue_additions"],
        duration_seconds=data["duration_seconds"],
        memories_processed=data["memories_processed"],
    )


def deserialize_rem_result(json_str: str) -> REMResult:
    """Deserialize REMResult from JSON."""
    from anima.dream.types import (
        DistantAssociation,
        GeneratedQuestion,
        SelfModelUpdate,
        UrgencyLevel,
    )

    data = json.loads(json_str)
    return REMResult(
        distant_associations=[
            DistantAssociation(
                memory_id_a=da["memory_id_a"],
                memory_id_b=da["memory_id_b"],
                content_a=da["content_a"],
                content_b=da["content_b"],
                connection_insight=da["connection_insight"],
                similarity=da["similarity"],
                urgency=UrgencyLevel(da["urgency"]),
            )
            for da in data["distant_associations"]
        ],
        generated_questions=[
            GeneratedQuestion(
                question=q["question"],
                source_memory_ids=q["source_memory_ids"],
                reasoning=q["reasoning"],
                urgency=UrgencyLevel(q["urgency"]),
            )
            for q in data["generated_questions"]
        ],
        self_model_updates=[
            SelfModelUpdate(
                observation=u["observation"],
                evidence_memory_ids=u["evidence_memory_ids"],
                pattern_type=u["pattern_type"],
                urgency=UrgencyLevel(u["urgency"]),
            )
            for u in data["self_model_updates"]
        ],
        diary_patterns_found=data["diary_patterns_found"],
        dream_journal_path=data["dream_journal_path"],
        curiosity_queue_additions=data["curiosity_queue_additions"],
        duration_seconds=data["duration_seconds"],
        iterations_completed=data["iterations_completed"],
    )
