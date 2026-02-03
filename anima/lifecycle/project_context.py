# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Project Context Fingerprinting - Phase 3A Semantic Project Loading.

Builds a semantic fingerprint of the current project by combining signals
from README, recent commits, and project metadata. This fingerprint is
used to find relevant PROJECT-scoped memories regardless of when they
were created.

Key insight from Matt: AGENT memories benefit from temporal recency (I evolve),
but PROJECT memories need semantic relevance (project rules persist).
A constraint like "always call Task-Review to validate" should surface
2 months later just as readily as 2 days later.

Usage:
    from anima.lifecycle.project_context import ProjectFingerprint

    fingerprint = ProjectFingerprint.from_directory(Path.cwd())
    relevant_memories = fingerprint.find_relevant_memories(store, agent_id, project_id)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from anima.core import Memory, RegionType
from anima.embeddings import embed_text
from anima.embeddings.similarity import find_similar
from anima.storage import MemoryStore
from anima.utils.git import get_recent_commits


# Files to check for README content (in priority order)
README_FILES = ["README.md", "README.rst", "README.txt", "README"]

# Files to check for project metadata
METADATA_FILES = [
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
]

# Maximum characters to include from README
MAX_README_CHARS = 2000

# Number of recent commits to include
RECENT_COMMITS_COUNT = 10

# Similarity threshold for matching PROJECT memories
PROJECT_MEMORY_THRESHOLD = 0.35


@dataclass
class ProjectFingerprint:
    """
    A semantic fingerprint of a project.

    Combines signals from various sources to create an embedding
    that represents "what this project is about".
    """

    project_name: str
    readme_excerpt: Optional[str] = None
    recent_commits: list[str] = field(default_factory=list)
    metadata_type: Optional[str] = None  # e.g., "python", "node", "rust"
    _embedding: Optional[list[float]] = field(default=None, repr=False)

    @classmethod
    def from_directory(
        cls,
        project_dir: Path,
        include_commits: bool = True,
        quiet: bool = True,
    ) -> "ProjectFingerprint":
        """
        Build a project fingerprint from a directory.

        Extracts signals from README, recent commits, and project metadata
        to create a semantic representation of the project.

        Args:
            project_dir: Path to the project root
            include_commits: Whether to include recent commit messages
            quiet: Suppress progress output

        Returns:
            ProjectFingerprint with extracted signals
        """
        project_name = project_dir.name

        # Extract README excerpt
        readme_excerpt = cls._extract_readme(project_dir)

        # Get recent commit messages
        recent_commits = []
        if include_commits:
            try:
                commits = get_recent_commits(count=RECENT_COMMITS_COUNT, cwd=project_dir)
                recent_commits = [c.get("message", "") for c in commits if c.get("message")]
            except Exception:
                pass  # Git not available or not a repo

        # Detect project type from metadata files
        metadata_type = cls._detect_project_type(project_dir)

        fingerprint = cls(
            project_name=project_name,
            readme_excerpt=readme_excerpt,
            recent_commits=recent_commits,
            metadata_type=metadata_type,
        )

        # Pre-generate embedding
        fingerprint._ensure_embedding(quiet=quiet)

        return fingerprint

    @staticmethod
    def _extract_readme(project_dir: Path) -> Optional[str]:
        """Extract the first portion of README for context."""
        for readme_name in README_FILES:
            readme_path = project_dir / readme_name
            if readme_path.exists():
                try:
                    content = readme_path.read_text(encoding="utf-8")
                    # Take first N characters, trying to break at paragraph
                    excerpt = content[:MAX_README_CHARS]
                    # Try to end at a paragraph break
                    last_para = excerpt.rfind("\n\n")
                    if last_para > MAX_README_CHARS // 2:
                        excerpt = excerpt[:last_para]
                    return excerpt.strip()
                except Exception:
                    pass
        return None

    @staticmethod
    def _detect_project_type(project_dir: Path) -> Optional[str]:
        """Detect project type from metadata files."""
        type_mapping = {
            "pyproject.toml": "python",
            "setup.py": "python",
            "requirements.txt": "python",
            "package.json": "node",
            "Cargo.toml": "rust",
            "go.mod": "go",
            "pom.xml": "java",
            "build.gradle": "java",
            "Gemfile": "ruby",
            "composer.json": "php",
        }

        for filename, project_type in type_mapping.items():
            if (project_dir / filename).exists():
                return project_type

        return None

    def to_text(self) -> str:
        """
        Convert fingerprint to text for embedding.

        Combines all signals into a single text representation.
        """
        parts = [f"Project: {self.project_name}"]

        if self.metadata_type:
            parts.append(f"Type: {self.metadata_type} project")

        if self.readme_excerpt:
            parts.append(f"Description: {self.readme_excerpt}")

        if self.recent_commits:
            commits_text = " | ".join(self.recent_commits[:5])  # Limit for embedding
            parts.append(f"Recent work: {commits_text}")

        return "\n".join(parts)

    def _ensure_embedding(self, quiet: bool = True) -> list[float]:
        """Ensure embedding is generated."""
        if self._embedding is None:
            text = self.to_text()
            self._embedding = embed_text(text, quiet=quiet)
        return self._embedding

    @property
    def embedding(self) -> list[float]:
        """Get the fingerprint embedding (generates if needed)."""
        return self._ensure_embedding()

    def find_relevant_memories(
        self,
        store: MemoryStore,
        agent_id: str,
        project_id: str,
        limit: int = 20,
        threshold: float = PROJECT_MEMORY_THRESHOLD,
        quiet: bool = True,
    ) -> list[Memory]:
        """
        Find PROJECT-scoped memories relevant to this project context.

        Uses semantic search to find memories that match the project
        fingerprint, regardless of when they were created.

        Args:
            store: Memory store to search
            agent_id: Agent ID for scoping
            project_id: Project ID (only searches this project's memories)
            limit: Maximum memories to return
            threshold: Minimum similarity threshold
            quiet: Suppress progress output

        Returns:
            List of relevant PROJECT memories, sorted by relevance
        """
        # Get PROJECT-scoped memories with embeddings
        candidate_memories = store.get_memories_with_embeddings(
            agent_id=agent_id,
            project_id=project_id,
            region=RegionType.PROJECT,  # Only PROJECT scope
        )

        if not candidate_memories:
            return []

        # Build candidates for similarity search
        candidates: list[tuple[str, list[float]]] = []
        for mem_id, content, emb in candidate_memories:
            if emb is not None:
                candidates.append((mem_id, emb))

        if not candidates:
            return []

        # Find similar memories
        fingerprint_embedding = self._ensure_embedding(quiet=quiet)
        results = find_similar(
            fingerprint_embedding,
            candidates,
            top_k=limit,
            threshold=threshold,
        )

        if not results:
            return []

        # Fetch full memory objects
        all_memories = store.get_memories_for_agent(
            agent_id=agent_id,
            project_id=project_id,
            region=RegionType.PROJECT,
        )

        # Return in similarity order
        id_to_memory = {m.id: m for m in all_memories}
        return [id_to_memory[r.item] for r in results if r.item in id_to_memory]


def get_project_relevant_memories(
    project_dir: Path,
    store: MemoryStore,
    agent_id: str,
    project_id: str,
    limit: int = 20,
    quiet: bool = True,
) -> list[Memory]:
    """
    Convenience function to get project-relevant memories.

    Builds a fingerprint and finds matching PROJECT memories in one call.

    Args:
        project_dir: Path to project root
        store: Memory store to search
        agent_id: Agent ID
        project_id: Project ID
        limit: Maximum memories to return
        quiet: Suppress progress output

    Returns:
        List of relevant PROJECT memories
    """
    fingerprint = ProjectFingerprint.from_directory(project_dir, quiet=quiet)
    return fingerprint.find_relevant_memories(
        store=store,
        agent_id=agent_id,
        project_id=project_id,
        limit=limit,
        quiet=quiet,
    )
