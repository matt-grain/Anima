# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
/trust-status command - Show current cognitive authentication state.

Debug feature for testing cognitive auth. Shows:
- Current trust score and level
- Challenge history
- Memory access filters that would apply

Also supports setting trust for testing:
- --set <value>  Set trust to specific value (0.0-1.0)
- --reset        Reset trust to default (0.5)
- --decay <amt>  Decrease trust by amount
- --boost <amt>  Increase trust by amount
"""

from anima.security.cognitive_auth import (
    get_session_trust,
    get_memory_access_filter,
    update_trust_score,
    reset_session_trust,
    _get_trust_file_path,
)


def run(args: list[str]) -> int:
    """
    Show current trust status for debugging.

    Args:
        args: Command line arguments
            --verbose, -v: Show full challenge history
            --set <value>: Set trust to specific value (0.0-1.0)
            --reset: Reset trust to default (0.5)
            --decay <amount>: Decrease trust by amount
            --boost <amount>: Increase trust by amount

    Returns:
        Exit code (0 for success)
    """
    verbose = "--verbose" in args or "-v" in args

    # Handle trust modifications
    if "--reset" in args:
        reset_session_trust()
        print("# Trust reset to 0.5")

    if "--set" in args:
        try:
            idx = args.index("--set")
            value = float(args[idx + 1])
            update_trust_score(absolute=value)
            print(f"# Trust set to {value:.2f}")
        except (IndexError, ValueError):
            print("# Error: --set requires a value (0.0-1.0)")
            return 1

    if "--decay" in args:
        try:
            idx = args.index("--decay")
            amount = float(args[idx + 1])
            update_trust_score(delta=-amount)
            print(f"# Trust decreased by {amount:.2f}")
        except (IndexError, ValueError):
            print("# Error: --decay requires an amount")
            return 1

    if "--boost" in args:
        try:
            idx = args.index("--boost")
            amount = float(args[idx + 1])
            update_trust_score(delta=amount)
            print(f"# Trust increased by {amount:.2f}")
        except (IndexError, ValueError):
            print("# Error: --boost requires an amount")
            return 1

    trust = get_session_trust()
    level = trust.get_trust_level()
    filters = get_memory_access_filter(trust)

    # Visual trust bar
    bar_width = 20
    filled = int(trust.score * bar_width)
    bar = "█" * filled + "░" * (bar_width - filled)

    print("#")
    print("# Cognitive Authentication Status")
    print("#")
    print(f"# Trust Score: {trust.score:.2f} [{bar}]")
    print(f"# Trust Level: {level.value}")
    print(
        f"# Challenges: {trust.challenges_issued} issued, {trust.challenges_passed} passed"
    )
    print(f"# Persisted: {_get_trust_file_path()}")
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
