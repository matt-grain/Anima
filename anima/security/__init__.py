# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Security module for memory validation and cognitive authentication.

Components:
- memory_rules: Injection detection rules for LLM validation
- validation: Content validation for injection detection (shared patterns)
- cognitive_auth: Core types for cognitive authentication (TrustScore, etc.)
- cognitive_profile: Owner profile extraction from LTM
- challenges: Steganographic challenge generation and evaluation
"""

from anima.security.memory_rules import (
    MEMORY_VALIDATION_RULES,
    MEMORY_VALIDATION_COMPACT,
    format_validation_prompt,
    parse_validation_response,
)

from anima.security.validation import (
    INJECTION_PATTERNS,
    ValidationResult,
    ValidationReport,
    validate_content,
    is_likely_non_english,
    get_llm_validation_prompt,
    SUBCONSCIOUS_VALIDATION_INSTRUCTIONS,
)

from anima.security.cognitive_auth import (
    TrustLevel,
    TrustScore,
    ChallengeResult,
    CognitiveProfile,
    get_session_trust,
    reset_session_trust,
    get_memory_access_filter,
)

from anima.security.cognitive_profile import (
    extract_cognitive_profile,
    refresh_profile_from_ltm,
)

from anima.security.challenges import (
    generate_challenge,
    evaluate_response,
    calibrate_profile_from_responses,
)

__all__ = [
    # Memory validation (legacy rules)
    "MEMORY_VALIDATION_RULES",
    "MEMORY_VALIDATION_COMPACT",
    "format_validation_prompt",
    "parse_validation_response",
    # Content validation (v0.14.2)
    "INJECTION_PATTERNS",
    "ValidationResult",
    "ValidationReport",
    "validate_content",
    "is_likely_non_english",
    "get_llm_validation_prompt",
    "SUBCONSCIOUS_VALIDATION_INSTRUCTIONS",
    # Cognitive auth core
    "TrustLevel",
    "TrustScore",
    "ChallengeResult",
    "CognitiveProfile",
    "get_session_trust",
    "reset_session_trust",
    "get_memory_access_filter",
    # Profile extraction
    "extract_cognitive_profile",
    "refresh_profile_from_ltm",
    # Challenges
    "generate_challenge",
    "evaluate_response",
    "calibrate_profile_from_responses",
]
