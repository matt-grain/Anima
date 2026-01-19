# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for auto-achievement detection.
"""

from anima.core import ImpactLevel
from anima.tools.detect_achievements import (
    detect_achievement,
    should_skip,
    ACHIEVEMENT_PATTERNS,
)


class TestShouldSkip:
    """Tests for skip pattern matching."""

    def test_skip_wip(self) -> None:
        """Test WIP commits are skipped."""
        assert should_skip("WIP: working on feature")
        assert should_skip("wip fix something")

    def test_skip_merge(self) -> None:
        """Test merge commits are skipped."""
        assert should_skip("Merge branch 'main'")
        assert should_skip("merge: feature into main")

    def test_skip_revert(self) -> None:
        """Test revert commits are skipped."""
        assert should_skip("Revert 'Add feature'")

    def test_skip_chore(self) -> None:
        """Test chore commits are skipped."""
        assert should_skip("chore: update dependencies")

    def test_skip_fixup(self) -> None:
        """Test fixup commits are skipped."""
        assert should_skip("fixup! Previous commit")

    def test_dont_skip_normal(self) -> None:
        """Test normal commits are not skipped."""
        assert not should_skip("Add new feature")
        assert not should_skip("Fix bug in login")


class TestDetectAchievement:
    """Tests for achievement detection."""

    def test_detect_add_command(self) -> None:
        """Test detection of 'Add X command' style."""
        result = detect_achievement("Add /memory-export and /memory-import commands")
        assert result is not None
        assert result[1] == ImpactLevel.HIGH

    def test_detect_add_feature(self) -> None:
        """Test detection of 'Add X feature' style."""
        result = detect_achievement("Add user authentication feature")
        assert result is not None

    def test_detect_add_tests(self) -> None:
        """Test detection of 'Add tests' style."""
        result = detect_achievement("Add tests for decay module")
        assert result is not None

    def test_detect_implement(self) -> None:
        """Test detection of 'Implement X' style."""
        result = detect_achievement("Implement new API endpoint")
        assert result is not None

    def test_detect_complete(self) -> None:
        """Test detection of 'Complete' keyword."""
        result = detect_achievement("Complete user dashboard")
        assert result is not None
        assert result[1] == ImpactLevel.HIGH

    def test_detect_version(self) -> None:
        """Test detection of version numbers."""
        result = detect_achievement("Release v1.0.0")
        assert result is not None
        assert result[1] == ImpactLevel.HIGH

    def test_detect_refactor(self) -> None:
        """Test detection of refactoring."""
        result = detect_achievement("Refactor authentication module")
        assert result is not None
        assert result[1] == ImpactLevel.MEDIUM

    def test_no_detection_simple_fix(self) -> None:
        """Test that simple fixes don't trigger achievement."""
        result = detect_achievement("Fix typo in README")
        assert result is None

    def test_no_detection_minor_update(self) -> None:
        """Test that minor updates don't trigger achievement."""
        result = detect_achievement("Update .gitignore")
        assert result is None

    def test_detect_critical_fix(self) -> None:
        """Test detection of critical fixes."""
        result = detect_achievement("Fix critical security vulnerability")
        assert result is not None
        assert result[1] == ImpactLevel.HIGH


class TestPatternCoverage:
    """Tests to ensure pattern coverage."""

    def test_all_patterns_are_tuples(self) -> None:
        """Test all patterns are (regex, ImpactLevel) tuples."""
        for pattern in ACHIEVEMENT_PATTERNS:
            assert isinstance(pattern, tuple)
            assert len(pattern) == 2
            assert isinstance(pattern[0], str)
            assert isinstance(pattern[1], ImpactLevel)
