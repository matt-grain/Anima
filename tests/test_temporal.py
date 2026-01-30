# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for temporal cue parser - "Time as Space" implementation."""

from datetime import datetime
from unittest.mock import patch, MagicMock

from anima.lifecycle.temporal import (
    TemporalCueType,
    TemporalCoordinate,
    parse_temporal_cue,
    find_all_temporal_cues,
)


class TestTemporalCoordinate:
    """Tests for TemporalCoordinate dataclass."""

    def test_has_filters_with_session(self):
        """Test filter detection with session ID."""
        coord = TemporalCoordinate(
            cue_type=TemporalCueType.SESSION,
            original_text="last session",
            session_id="abc123",
        )
        assert coord.has_filters() is True

    def test_has_filters_with_git(self):
        """Test filter detection with git commit."""
        coord = TemporalCoordinate(
            cue_type=TemporalCueType.GIT_EVENT,
            original_text="last commit",
            git_commit="abc123",
        )
        assert coord.has_filters() is True

    def test_has_filters_with_time_range(self):
        """Test filter detection with time range."""
        coord = TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text="yesterday",
            start_time=datetime.now(),
        )
        assert coord.has_filters() is True

    def test_has_no_filters(self):
        """Test detection of empty coordinate."""
        coord = TemporalCoordinate(
            cue_type=TemporalCueType.RELATIVE_TIME,
            original_text="unknown",
        )
        assert coord.has_filters() is False


class TestParseSessionCues:
    """Tests for session-based temporal cues."""

    @patch("anima.lifecycle.temporal.get_previous_session_id")
    def test_last_session_direct(self, mock_prev):
        """Test 'last session' detection."""
        mock_prev.return_value = "prev-session-id"

        coord = parse_temporal_cue("What did we discuss last session?")
        assert coord is not None
        assert coord.cue_type == TemporalCueType.SESSION
        assert coord.session_id == "prev-session-id"

    @patch("anima.lifecycle.temporal.get_previous_session_id")
    def test_previous_session(self, mock_prev):
        """Test 'previous session' detection."""
        mock_prev.return_value = "prev-id"

        coord = parse_temporal_cue("In the previous session we worked on X")
        assert coord is not None
        assert coord.cue_type == TemporalCueType.SESSION
        assert coord.session_id == "prev-id"

    @patch("anima.lifecycle.temporal.get_previous_session_id")
    def test_as_we_discussed_last_session(self, mock_prev):
        """Test 'as we discussed last session' pattern."""
        mock_prev.return_value = "prev-id"

        coord = parse_temporal_cue("As we discussed last session, the API needs work")
        assert coord is not None
        assert coord.session_id == "prev-id"

    @patch("anima.lifecycle.temporal.get_current_session_id")
    def test_current_session(self, mock_current):
        """Test 'this session' detection."""
        mock_current.return_value = "current-id"

        coord = parse_temporal_cue("Earlier this session we fixed the bug")
        assert coord is not None
        assert coord.cue_type == TemporalCueType.SESSION
        assert coord.session_id == "current-id"
        assert coord.is_current_session is True


class TestParseGitCues:
    """Tests for git-based temporal cues."""

    @patch("anima.lifecycle.temporal.get_recent_commits")
    def test_last_commit(self, mock_commits):
        """Test 'last commit' detection."""
        mock_commits.return_value = [
            {"hash": "abc123", "subject": "Current"},
            {"hash": "def456", "subject": "Previous"},
        ]

        coord = parse_temporal_cue("What was the context during the last commit?")
        assert coord is not None
        assert coord.cue_type == TemporalCueType.GIT_EVENT
        assert coord.git_commit == "def456"

    @patch("anima.lifecycle.temporal.get_git_context")
    def test_current_commit(self, mock_ctx):
        """Test 'this commit' detection."""
        mock_ctx.return_value = MagicMock(commit="abc123")

        coord = parse_temporal_cue("For this commit we need to remember...")
        assert coord is not None
        assert coord.git_commit == "abc123"

    def test_git_main_branch(self):
        """Test 'on main branch' detection."""
        coord = parse_temporal_cue("What did we do on main?")
        assert coord is not None
        assert coord.cue_type == TemporalCueType.GIT_EVENT
        assert coord.git_branch == "main"

    def test_git_master_branch(self):
        """Test 'on master branch' detection."""
        coord = parse_temporal_cue("Changes made on master branch")
        assert coord is not None
        assert coord.git_branch == "master"

    def test_git_feature_branch(self):
        """Test 'on branch X' detection."""
        coord = parse_temporal_cue("We worked on the branch feature/auth")
        assert coord is not None
        assert coord.git_branch == "feature/auth"


class TestParseRelativeTimeCues:
    """Tests for relative time cues."""

    def test_yesterday(self):
        """Test 'yesterday' detection."""
        now = datetime(2026, 1, 30, 15, 0, 0)
        coord = parse_temporal_cue("What did we do yesterday?", now=now)

        assert coord is not None
        assert coord.cue_type == TemporalCueType.RELATIVE_TIME
        assert coord.start_time == datetime(2026, 1, 29, 0, 0, 0)
        assert coord.end_time == datetime(2026, 1, 30, 0, 0, 0)

    def test_last_week(self):
        """Test 'last week' detection."""
        now = datetime(2026, 1, 30, 15, 0, 0)
        coord = parse_temporal_cue("What happened last week?", now=now)

        assert coord is not None
        assert coord.start_time is not None
        assert (now - coord.start_time).days == 7

    def test_recently(self):
        """Test 'recently' detection (48 hours)."""
        now = datetime(2026, 1, 30, 15, 0, 0)
        coord = parse_temporal_cue("We recently discussed this", now=now)

        assert coord is not None
        assert coord.start_time is not None
        hours_diff = (now - coord.start_time).total_seconds() / 3600
        assert abs(hours_diff - 48) < 1

    def test_this_week(self):
        """Test 'this week' detection."""
        # Thursday Jan 30
        now = datetime(2026, 1, 30, 15, 0, 0)
        coord = parse_temporal_cue("What did we work on this week?", now=now)

        assert coord is not None
        assert coord.start_time is not None
        # Should start on Monday (Jan 27)
        assert coord.start_time.weekday() == 0

    def test_few_days_ago(self):
        """Test 'a few days ago' detection."""
        now = datetime(2026, 1, 30, 15, 0, 0)
        coord = parse_temporal_cue("A few days ago we fixed something", now=now)

        assert coord is not None
        # Should be 1-5 days ago
        assert (now - coord.start_time).days == 5
        assert (now - coord.end_time).days == 1

    def test_last_month(self):
        """Test 'last month' detection."""
        now = datetime(2026, 1, 30, 15, 0, 0)
        coord = parse_temporal_cue("We discussed this last month", now=now)

        assert coord is not None
        assert (now - coord.start_time).days == 30


class TestParseNoCues:
    """Tests for text without temporal cues."""

    def test_no_temporal_cue(self):
        """Test that non-temporal text returns None."""
        coord = parse_temporal_cue("How do I implement authentication?")
        assert coord is None

    def test_technical_question(self):
        """Test that technical questions don't trigger."""
        coord = parse_temporal_cue("What is the best practice for error handling?")
        assert coord is None


class TestFindAllCues:
    """Tests for finding multiple temporal cues."""

    @patch("anima.lifecycle.temporal.get_previous_session_id")
    @patch("anima.lifecycle.temporal.get_recent_commits")
    def test_multiple_cues(self, mock_commits, mock_prev):
        """Test finding multiple cues in one message."""
        mock_prev.return_value = "prev-session"
        mock_commits.return_value = [
            {"hash": "abc", "subject": "Current"},
            {"hash": "def", "subject": "Previous"},
        ]

        text = "Last session we discussed this, and during the last commit we implemented it"
        cues = find_all_temporal_cues(text)

        assert len(cues) >= 2
        cue_types = {c.cue_type for c in cues}
        assert TemporalCueType.SESSION in cue_types
        assert TemporalCueType.GIT_EVENT in cue_types

    def test_repeated_cue(self):
        """Test handling of repeated same cue."""
        text = "Yesterday we did X and yesterday we did Y"
        cues = find_all_temporal_cues(text)

        # Should find both occurrences
        assert len(cues) == 2


class TestIntegrationScenarios:
    """Integration tests for real-world scenarios."""

    @patch("anima.lifecycle.temporal.get_previous_session_id")
    def test_builds_on_scenario(self, mock_prev):
        """Test scenario: user references previous work."""
        mock_prev.return_value = "20260129-143022-abc12345"

        text = "As we mentioned last session, the auth module needs refactoring"
        coord = parse_temporal_cue(text)

        assert coord is not None
        assert coord.session_id == "20260129-143022-abc12345"
        # This coordinate can now be used to query memories from that session

    @patch("anima.lifecycle.temporal.get_recent_commits")
    def test_git_correlation_scenario(self, mock_commits):
        """Test scenario: user references code changes."""
        mock_commits.return_value = [
            {"hash": "a1b2c3d", "subject": "Add auth"},
            {"hash": "e4f5g6h", "subject": "Fix bug"},
        ]

        text = "During the last commit, what decisions did we make?"
        coord = parse_temporal_cue(text)

        assert coord is not None
        assert coord.git_commit == "e4f5g6h"
        # This can be used to find memories linked to this commit

    def test_relative_time_scenario(self):
        """Test scenario: user uses relative time."""
        now = datetime(2026, 1, 30, 15, 0, 0)
        text = "I remember we discussed caching yesterday"
        coord = parse_temporal_cue(text, now=now)

        assert coord is not None
        assert coord.start_time is not None
        # Can use start_time/end_time to filter memories by created_at
