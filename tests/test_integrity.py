# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for memory integrity validation.
"""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from anima.core import Agent, Memory, MemoryKind, ImpactLevel, RegionType
from anima.lifecycle.integrity import (
    MemoryIntegrityChecker,
    IntegrityIssue,
    IntegrityReport,
)


class TestIntegrityIssue:
    """Tests for IntegrityIssue."""

    def test_str_format(self) -> None:
        """Test string representation."""
        issue = IntegrityIssue(
            memory_id="abc12345-1234-1234-1234-123456789012",
            field="content",
            issue="Empty content",
            severity="error",
        )
        assert "[ERROR] abc12345: content - Empty content" == str(issue)

    def test_warning_format(self) -> None:
        """Test warning severity format."""
        issue = IntegrityIssue(
            memory_id="def12345-1234-1234-1234-123456789012",
            field="confidence",
            issue="Out of range",
            severity="warning",
        )
        assert "[WARNING] def12345: confidence - Out of range" == str(issue)


class TestIntegrityReport:
    """Tests for IntegrityReport."""

    def test_healthy_report(self) -> None:
        """Test healthy report with no issues."""
        report = IntegrityReport(total_checked=10, issues=[])
        assert report.is_healthy
        assert report.error_count == 0
        assert report.warning_count == 0
        assert "10 memories checked, all healthy" in str(report)

    def test_report_with_errors(self) -> None:
        """Test report with errors."""
        issues = [
            IntegrityIssue("id1", "content", "Empty", "error"),
            IntegrityIssue("id2", "agent_id", "Missing", "error"),
            IntegrityIssue("id3", "confidence", "Out of range", "warning"),
        ]
        report = IntegrityReport(total_checked=10, issues=issues)
        assert not report.is_healthy
        assert report.error_count == 2
        assert report.warning_count == 1
        assert "2 errors" in str(report)
        assert "1 warnings" in str(report)


class TestMemoryIntegrityChecker:
    """Tests for MemoryIntegrityChecker."""

    def test_check_healthy_memory(self) -> None:
        """Test that a healthy memory passes all checks."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            region=RegionType.AGENT,
            kind=MemoryKind.LEARNINGS,
            content="This is a valid memory",
            impact=ImpactLevel.HIGH,
            confidence=0.9,
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert report.is_healthy
        assert report.total_checked == 1

    def test_check_missing_agent_id(self) -> None:
        """Test detection of missing agent_id."""
        memory = Memory(
            id="test-id",
            agent_id="",  # Missing!
            content="Content here",
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert not report.is_healthy
        assert report.error_count >= 1
        assert any(i.field == "agent_id" for i in report.issues)

    def test_check_empty_content(self) -> None:
        """Test detection of empty content."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            content="",  # Empty!
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert not report.is_healthy
        assert any(i.field == "content" for i in report.issues)

    def test_check_invalid_confidence(self) -> None:
        """Test detection of out-of-range confidence."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            content="Valid content",
            confidence=1.5,  # Out of range!
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert not report.is_healthy
        assert report.warning_count >= 1
        assert any(i.field == "confidence" for i in report.issues)

    def test_check_negative_confidence(self) -> None:
        """Test detection of negative confidence."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            content="Valid content",
            confidence=-0.5,  # Negative!
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert not report.is_healthy
        assert any(i.field == "confidence" for i in report.issues)

    def test_check_orphaned_previous_memory(self) -> None:
        """Test detection of orphaned previous_memory_id reference."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            content="Valid content",
            previous_memory_id="non-existent-id",  # Orphaned!
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert not report.is_healthy
        assert report.warning_count >= 1
        assert any(i.field == "previous_memory_id" for i in report.issues)

    def test_check_orphaned_superseded_by(self) -> None:
        """Test detection of orphaned superseded_by reference."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            content="Valid content",
            superseded_by="non-existent-id",  # Orphaned!
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert not report.is_healthy
        assert any(i.field == "superseded_by" for i in report.issues)

    def test_check_valid_previous_memory_reference(self) -> None:
        """Test that valid previous_memory_id passes."""
        memory1 = Memory(
            id="first-id",
            agent_id="anima",
            content="First memory",
        )
        memory2 = Memory(
            id="second-id",
            agent_id="anima",
            content="Second memory",
            previous_memory_id="first-id",  # Valid reference
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory1, memory2]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert report.is_healthy
        assert report.total_checked == 2

    def test_check_invalid_signature(self) -> None:
        """Test detection of invalid signature."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            content="Valid content",
            signature="invalid-signature",
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        with patch("anima.lifecycle.integrity.verify_signature") as mock_verify:
            mock_verify.return_value = False

            checker = MemoryIntegrityChecker(mock_store)
            report = checker.check_all(agent_id="anima", signing_key="test-key")

            assert not report.is_healthy
            assert report.error_count >= 1
            assert any(i.field == "signature" for i in report.issues)

    def test_check_valid_signature(self) -> None:
        """Test that valid signature passes."""
        memory = Memory(
            id="test-id",
            agent_id="anima",
            content="Valid content",
            signature="valid-signature",
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        with patch("anima.lifecycle.integrity.verify_signature") as mock_verify:
            mock_verify.return_value = True

            checker = MemoryIntegrityChecker(mock_store)
            report = checker.check_all(agent_id="anima", signing_key="test-key")

            assert report.is_healthy

    def test_check_multiple_issues_same_memory(self) -> None:
        """Test that multiple issues in one memory are all reported."""
        memory = Memory(
            id="test-id",
            agent_id="",  # Missing
            content="",  # Empty
            confidence=2.0,  # Out of range
            previous_memory_id="orphan",  # Orphaned
        )

        mock_store = MagicMock()
        mock_store.get_memories_for_agent.return_value = [memory]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima")

        assert not report.is_healthy
        assert len(report.issues) >= 4

    def test_check_with_project_memories(self) -> None:
        """Test that project and agent memories are both checked."""
        agent_memory = Memory(
            id="agent-mem",
            agent_id="anima",
            region=RegionType.AGENT,
            content="Agent memory",
        )
        project_memory = Memory(
            id="project-mem",
            agent_id="anima",
            region=RegionType.PROJECT,
            project_id="test-project",
            content="Project memory",
        )

        mock_store = MagicMock()
        # First call returns project memories, second call returns agent memories
        mock_store.get_memories_for_agent.side_effect = [
            [project_memory],
            [agent_memory],
        ]

        checker = MemoryIntegrityChecker(mock_store)
        report = checker.check_all(agent_id="anima", project_id="test-project")

        assert report.is_healthy
        assert report.total_checked == 2
