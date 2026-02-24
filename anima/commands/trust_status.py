# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/trust-status command - Show current cognitive authentication state.

Debug feature for testing cognitive auth. Shows:
- Current trust score and level
- Challenge history
- Memory access filters that would apply
"""

from anima.security.cognitive_auth import (
    get_session_trust,
    get_memory_access_filter,
)


def run(args: list[str]) -> int:
    """
    Show current trust status for debugging.

    Args:
        args: Command line arguments (--verbose for full history)

    Returns:
        Exit code (0 for success)
    """
    verbose = "--verbose" in args or "-v" in args

    trust = get_session_trust()
    level = trust.get_trust_level()
    filters = get_memory_access_filter(trust)

    # Visual trust bar
    bar_width = 20
    filled = int(trust.score * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    print("# Cognitive Authentication Status")
    print("#")
    print(f"# Trust Score: {trust.score:.2f} [{bar}]")
    print(f"# Trust Level: {level.value}")
    print(
        f"# Challenges: {trust.challenges_issued} issued, {trust.challenges_passed} passed"
    )
    print("#")

    # Show what filters would apply
    if filters:
        print("# Memory Access Filters (current):")
        for key, value in filters.items():
            print(f"#   - {key}: {value}")
    else:
        print("# Memory Access: FULL (no restrictions)")

    print("#")

    # Interpretation
    if level.value == "FULL":
        print("# Status: Owner verified. Full memory access.")
    elif level.value == "PARTIAL":
        print("# Status: Benefit of the doubt. Recent memories only.")
    elif level.value == "MINIMAL":
        print("# Status: Verification needed. CORE memories only.")
    else:  # SUSPICIOUS
        print("# Status: ⚠️  Trust degraded. Critical memories only, logging active.")

    if verbose and trust.challenge_history:
        print("#")
        print("# Challenge History:")
        for result in trust.challenge_history[-5:]:  # Last 5
            status = "✓" if result.match_score >= 0.5 else "✗"
            print(f"#   [{status}] {result.challenge_type}: {result.match_score:.2f}")

    return 0
