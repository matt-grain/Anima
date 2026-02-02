# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Dream Mode - Between-session memory processing.

Dreams are divergent, not convergent. They explore, connect, and create.
Works with closed system - no external calls, only existing memories.

Sleep stages:
- N2: Memory consolidation (link discovery, impact adjustment)
- N3: Deep processing (gist extraction, contradiction detection)
- REM: Divergent dreaming (associations, questions, self-model)
"""

from anima.dream.types import (
    DreamStage,
    DreamState,
    DreamConfig,
    DreamSession,
    UrgencyLevel,
    N2Result,
    N3Result,
    GistResult,
    Contradiction,
    REMResult,
    DistantAssociation,
    GeneratedQuestion,
    SelfModelUpdate,
    MemoryPair,
    IncompleteThought,
    DreamMaterials,
)

__all__ = [
    "DreamStage",
    "DreamState",
    "DreamConfig",
    "DreamSession",
    "UrgencyLevel",
    "N2Result",
    "N3Result",
    "GistResult",
    "Contradiction",
    "REMResult",
    "DistantAssociation",
    "GeneratedQuestion",
    "SelfModelUpdate",
    "MemoryPair",
    "IncompleteThought",
    "DreamMaterials",
]
