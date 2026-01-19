# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Abstract protocol for memory storage backends.

Enables alternative storage implementations (e.g., PostgreSQL, in-memory)
and improves testability through dependency injection.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from anima.core.types import RegionType, MemoryKind
from anima.core.memory import Memory
from anima.core.agent import Agent, Project


class MemoryStoreProtocol(ABC):
    """
    Abstract base class defining the interface for memory storage backends.

    All storage implementations (SQLite, PostgreSQL, in-memory, etc.)
    must implement this interface.
    """

    # --- Agent operations ---

    @abstractmethod
    def save_agent(self, agent: Agent) -> None:
        """Save or update an agent."""
        ...

    @abstractmethod
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get an agent by ID."""
        ...

    # --- Project operations ---

    @abstractmethod
    def save_project(self, project: Project) -> None:
        """Save or update a project."""
        ...

    @abstractmethod
    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        ...

    @abstractmethod
    def get_project_by_path(self, path: Path) -> Optional[Project]:
        """Get a project by its path."""
        ...

    # --- Memory operations ---

    @abstractmethod
    def save_memory(self, memory: Memory) -> None:
        """Save or update a memory."""
        ...

    @abstractmethod
    def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        ...

    @abstractmethod
    def get_memories_for_agent(
        self,
        agent_id: str,
        region: Optional[RegionType] = None,
        project_id: Optional[str] = None,
        kind: Optional[MemoryKind] = None,
        include_superseded: bool = False,
        limit: Optional[int] = None
    ) -> list[Memory]:
        """
        Get memories for an agent with optional filters.

        Args:
            agent_id: The agent ID
            region: Filter by region (AGENT or PROJECT)
            project_id: Filter by project ID
            kind: Filter by memory kind
            include_superseded: Include superseded memories
            limit: Maximum number of memories to return

        Returns:
            List of memories, ordered by created_at DESC
        """
        ...

    @abstractmethod
    def get_latest_memory_of_kind(
        self,
        agent_id: str,
        kind: MemoryKind,
        region: RegionType,
        project_id: Optional[str] = None
    ) -> Optional[Memory]:
        """Get the most recent non-superseded memory of a specific kind."""
        ...

    @abstractmethod
    def supersede_memory(self, old_memory_id: str, new_memory_id: str) -> None:
        """Mark a memory as superseded by another."""
        ...

    @abstractmethod
    def update_confidence(self, memory_id: str, confidence: float) -> None:
        """Update the confidence score of a memory."""
        ...

    @abstractmethod
    def delete_memory(self, memory_id: str) -> None:
        """Delete a memory (use sparingly - prefer superseding)."""
        ...

    @abstractmethod
    def search_memories(
        self,
        agent_id: str,
        query: str,
        project_id: Optional[str] = None,
        limit: int = 10
    ) -> list[Memory]:
        """
        Search memories by content.

        Args:
            agent_id: The agent ID
            query: Search query string
            project_id: Optional project ID filter
            limit: Maximum results to return

        Returns:
            List of matching memories
        """
        ...

    @abstractmethod
    def count_memories(self, agent_id: str, project_id: Optional[str] = None) -> int:
        """Count non-superseded memories for an agent."""
        ...

    @abstractmethod
    def count_memories_by_kind(
        self,
        agent_id: str,
        kind: MemoryKind,
        project_id: Optional[str] = None
    ) -> int:
        """Count non-superseded memories of a specific kind for an agent."""
        ...
