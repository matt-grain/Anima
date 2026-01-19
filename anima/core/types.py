# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Core types and enums for LTM."""

from enum import Enum


class RegionType(str, Enum):
    """Memory region types."""
    AGENT = "AGENT"      # Cross-project memories for this agent
    PROJECT = "PROJECT"  # Project-specific memories


class MemoryKind(str, Enum):
    """Types of memories."""
    EMOTIONAL = "EMOTIONAL"        # Relationship patterns, communication style
    ARCHITECTURAL = "ARCHITECTURAL"  # Technical foundations, patterns, rules
    LEARNINGS = "LEARNINGS"        # Lessons learned, errors to avoid
    ACHIEVEMENTS = "ACHIEVEMENTS"  # Completed work, milestones


class ImpactLevel(str, Enum):
    """Memory impact levels - affects decay rate."""
    LOW = "LOW"          # Aggressive decay after 1 day
    MEDIUM = "MEDIUM"    # Moderate decay after 1 week
    HIGH = "HIGH"        # Gentle decay after 1 month
    CRITICAL = "CRITICAL"  # Never decay, keep full detail
