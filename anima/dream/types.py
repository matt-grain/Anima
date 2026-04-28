# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Dream Mode type definitions.

Data structures for dream stage configuration and results.
"""

from dataclasses import dataclass, field
from enum import Enum


class DreamStage(str, Enum):
    """Sleep stages for dream processing."""

    CLEANUP = "CLEANUP"  # Memory hygiene (dedup, decay, prune stale)
    N2 = "N2"  # Memory consolidation (systematic, housekeeping)
    N3 = "N3"  # Deep processing (analytical, reductive)
    REM = "REM"  # Divergent dreaming (wandering, associative)


class DreamState(str, Enum):
    """FSM states for dream crash recovery."""

    IDLE = "IDLE"  # No dream in progress
    CLEANUP_RUNNING = "CLEANUP_RUNNING"  # Cleanup stage in progress
    CLEANUP_COMPLETE = "CLEANUP_COMPLETE"  # Cleanup done, ready for N2
    N2_RUNNING = "N2_RUNNING"  # N2 stage in progress
    N2_COMPLETE = "N2_COMPLETE"  # N2 done, ready for N3
    N3_RUNNING = "N3_RUNNING"  # N3 stage in progress
    N3_COMPLETE = "N3_COMPLETE"  # N3 done, ready for REM
    REM_RUNNING = "REM_RUNNING"  # REM stage in progress
    COMPLETE = "COMPLETE"  # All stages done


class UrgencyLevel(str, Enum):
    """Urgency level for dream insights."""

    MEH = "MEH"  # Interesting but not urgent
    WORTH_MENTIONING = "WORTH_MENTIONING"  # Bring up when relevant
    IMPORTANT = "IMPORTANT"  # Discuss soon
    CRITICAL = "CRITICAL"  # WAKE UP MATT!


@dataclass
class DreamConfig:
    """Configuration for dream execution."""

    # Which stages to run
    stages: list[DreamStage] = field(
        default_factory=lambda: [
            DreamStage.CLEANUP,
            DreamStage.N2,
            DreamStage.N3,
            DreamStage.REM,
        ]
    )

    # N2 configuration
    n2_similarity_threshold: float = 0.6  # Higher than normal (0.5) to reduce noise
    n2_max_links_per_memory: int = 3  # Max new links per memory
    n2_process_limit: int = 100  # Max memories to process per run

    # N3 configuration (Phase 2)
    n3_gist_max_tokens: int = 50  # Target gist length
    n3_contradiction_threshold: float = 0.7  # High similarity for contradiction check

    # REM configuration (Phase 3)
    rem_association_distance: float = 0.3  # Look for distant connections
    rem_max_iterations: int = 5  # Bounded wandering (avoid AI coma!)
    rem_temperature: float = 0.9  # Higher creativity

    # Cleanup configuration
    cleanup_wip_max_age_days: int = 7  # Delete WIP memories older than this
    cleanup_low_max_age_days: int = 14  # Delete LOW impact older than this
    cleanup_duplicate_threshold: float = 0.9  # Similarity above this = duplicate
    cleanup_dry_run: bool = False  # If True, report but don't delete

    # General
    project_lookback_days: int = 7  # Process memories from last N days
    diary_lookback_days: int = 7  # Process diaries from last N days
    include_agent_memories: bool = True
    include_project_memories: bool = True


@dataclass
class SuspiciousMemory:
    """A memory flagged as potentially malicious or injected."""

    memory_id: str
    content_preview: str  # First 100 chars
    reason: str  # Why it was flagged
    pattern_matched: str  # Which pattern triggered detection
    quarantined: bool  # True if moved to quarantine, False if just flagged


@dataclass
class CleanupResult:
    """Results from cleanup stage."""

    # Forgotten memories deleted
    forgotten_deleted: int

    # Stale WIP memories deleted
    wip_deleted: int

    # Duplicates handled
    duplicates_found: int
    duplicates_deleted: int  # SUBCONSCIOUS duplicates
    duplicates_merged: int  # Other kinds merged

    # LOW impact old memories deleted
    low_impact_deleted: int

    # Suspicious memories (injection detection)
    suspicious_found: int = 0
    suspicious_quarantined: int = 0

    # Stats
    duration_seconds: float = 0.0
    memories_scanned: int = 0
    total_deleted: int = 0

    # Details for verbose output
    deleted_ids: list[str] = field(default_factory=list)
    merged_pairs: list[tuple[str, str]] = field(default_factory=list)  # (kept_id, deleted_id)
    suspicious_memories: list[SuspiciousMemory] = field(default_factory=list)


@dataclass
class SubconsciousIntegration:
    """Result of integrating a subconscious memory with conscious ones."""

    subconscious_id: str
    conscious_id: str  # The nearest conscious memory
    similarity: float
    action: str  # "merged", "linked", "kept_separate"


@dataclass
class N2Result:
    """Results from N2 consolidation stage."""

    new_links_found: int
    links: list[tuple[str, str, str, float]]  # (source_id, target_id, link_type, similarity)
    impact_adjustments: list[tuple[str, str, str]]  # (memory_id, old_impact, new_impact)
    duration_seconds: float
    memories_processed: int
    # Subconscious integration (Phase 0)
    subconscious_merged: int = 0
    subconscious_linked: int = 0
    subconscious_kept: int = 0
    subconscious_integrations: list[SubconsciousIntegration] = field(default_factory=list)


@dataclass
class GistResult:
    """Result of gist extraction for a memory."""

    memory_id: str
    original_length: int
    gist: str
    gist_length: int

    @property
    def compression_ratio(self) -> float:
        """How much the content was compressed (0-1, lower = more compression)."""
        if self.original_length == 0:
            return 1.0
        return self.gist_length / self.original_length


@dataclass
class Contradiction:
    """A detected contradiction between two memories."""

    memory_id_a: str
    memory_id_b: str
    content_a: str
    content_b: str
    description: str
    similarity: float  # Paradoxically high for contradictions


@dataclass
class ScopeIssue:
    """A memory that might be in the wrong region (AGENT vs PROJECT)."""

    memory_id: str
    content: str
    current_region: str  # 'AGENT' or 'PROJECT'
    current_project_id: str | None
    suggested_region: str  # 'AGENT' or 'PROJECT'
    suggested_project_id: str | None
    reason: str  # Why we think it's misplaced


@dataclass
class N3Result:
    """Results from N3 deep processing stage."""

    gists_created: int
    gist_results: list[GistResult]
    contradictions_found: int
    contradictions: list[Contradiction]
    dissonance_queue_additions: int
    duration_seconds: float
    memories_processed: int
    # v7: Memory scope validation
    memories_validated: int = 0  # Auto-validated (clear scope)
    scope_issues_found: int = 0  # Flagged for human review
    scope_issues: list[ScopeIssue] = field(default_factory=list)


@dataclass
class DistantAssociation:
    """A surprising connection between semantically distant memories."""

    memory_id_a: str
    memory_id_b: str
    content_a: str
    content_b: str
    connection_insight: str  # Why this connection is interesting
    similarity: float  # Low similarity = more surprising
    urgency: UrgencyLevel = UrgencyLevel.WORTH_MENTIONING


@dataclass
class GeneratedQuestion:
    """A new curiosity generated from existing knowledge."""

    question: str
    source_memory_ids: list[str]
    reasoning: str  # Why this question emerged
    urgency: UrgencyLevel = UrgencyLevel.MEH


@dataclass
class SelfModelUpdate:
    """An observation about how I work."""

    observation: str
    evidence_memory_ids: list[str]
    pattern_type: str  # "behavioral", "preference", "capability", "tendency"
    urgency: UrgencyLevel = UrgencyLevel.WORTH_MENTIONING


@dataclass
class REMResult:
    """Results from REM divergent dreaming stage."""

    distant_associations: list[DistantAssociation]
    generated_questions: list[GeneratedQuestion]
    self_model_updates: list[SelfModelUpdate]
    diary_patterns_found: list[str]
    dream_journal_path: str | None  # Path to generated diary entry
    curiosity_queue_additions: int
    duration_seconds: float
    iterations_completed: int


@dataclass
class DreamSession:
    """Persisted dream session for crash recovery."""

    id: str
    agent_id: str
    project_id: str | None
    state: DreamState
    started_at: str  # ISO format
    updated_at: str  # ISO format
    n2_result_json: str | None = None  # Serialized N2Result
    n3_result_json: str | None = None  # Serialized N3Result
    rem_result_json: str | None = None  # Serialized REMResult


@dataclass
class MemoryPair:
    """A pair of memories for dream reflection."""

    memory_a_id: str
    memory_a_content: str
    memory_b_id: str
    memory_b_content: str
    similarity: float  # Low = more distant/interesting


@dataclass
class IncompleteThought:
    """An incomplete thought found in memories."""

    memory_id: str
    snippet: str
    signal_type: str  # "wonder", "todo", "unclear", etc.


@dataclass
class DreamMaterials:
    """Raw materials gathered for lucid dreaming.

    This is what the code gathers. The actual dream reflection
    happens conversationally when I think about these materials.
    """

    # Memory pairs with low similarity (distant concepts to connect)
    distant_pairs: list[MemoryPair]

    # Incomplete thoughts found in memories
    incomplete_thoughts: list[IncompleteThought]

    # Recurring keywords across memories
    recurring_themes: list[str]

    # Diary snippets for pattern mining
    diary_snippets: list[tuple[str, str]]  # (date, excerpt)

    # Statistics for context
    total_memories: int
    total_diary_entries: int

    # Fields with defaults must come after non-default fields
    recent_memories_count: int = 0  # New since last dream
    random_old_memories_count: int = 0  # Random older memories mixed in
    recent_diaries_count: int = 0  # New since last dream
    random_old_diaries_count: int = 0  # Random older diaries mixed in

    # Contradiction candidates from N3 (to be evaluated during lucid dream)
    contradiction_candidates: list[Contradiction] = field(default_factory=list)

    # Path to template file (if created)
    template_path: str | None = None
