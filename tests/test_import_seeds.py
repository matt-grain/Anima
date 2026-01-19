# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM seed memory importer.
"""

from datetime import datetime
from pathlib import Path
from textwrap import dedent

import pytest

from anima.core import MemoryKind, ImpactLevel, RegionType
from anima.tools import import_seeds


class TestParseSeedFile:
    """Tests for seed file parsing."""

    def test_parse_valid_seed_file(self, tmp_path: Path) -> None:
        """Test parsing a valid seed file."""
        seed_content = dedent("""
            # Test Memory

            **ID:** LEARN-2025-12-20-001
            **Created:** 2025-12-20
            **Impact:** HIGH
            **Region:** AGENT
            **Confidence:** 1.0

            ## Raw Memory (Original)

            This is the raw memory content about testing.
            It spans multiple lines.

            ## Compacted Memory (For Injection)
            ```
            ~LEARN:HIGH| Testing best practices
            ```
        """).strip()

        seed_file = tmp_path / "test_memory.md"
        seed_file.write_text(seed_content)

        result = import_seeds.parse_seed_file(seed_file)

        assert result is not None
        assert result["id"] == "LEARN-2025-12-20-001"
        assert result["created_at"] == datetime(2025, 12, 20)
        assert result["impact"] == ImpactLevel.HIGH
        assert result["region"] == RegionType.AGENT
        assert result["confidence"] == 1.0
        assert result["kind"] == MemoryKind.LEARNINGS
        assert "raw memory content" in result["raw_content"]
        assert "Testing best practices" in result["compacted_content"]

    def test_parse_seed_with_project_region(self, tmp_path: Path) -> None:
        """Test parsing a seed file with PROJECT region."""
        seed_content = dedent("""
            # Project Memory

            **ID:** ARCH-2025-12-20-001
            **Created:** 2025-12-20
            **Impact:** CRITICAL
            **Region:** PROJECT (LTM)
            **Confidence:** 0.9

            ## Raw Memory (Original)

            Architecture decision for LTM project.

            ## Compacted Memory (For Injection)
            ```
            ~ARCH:CRIT| LTM architecture
            ```
        """).strip()

        seed_file = tmp_path / "project_memory.md"
        seed_file.write_text(seed_content)

        result = import_seeds.parse_seed_file(seed_file)

        assert result is not None
        assert result["region"] == RegionType.PROJECT
        assert result["project"] == "LTM"
        assert result["kind"] == MemoryKind.ARCHITECTURAL
        assert result["confidence"] == 0.9

    def test_parse_emotional_memory(self, tmp_path: Path) -> None:
        """Test parsing an emotional memory seed file."""
        seed_content = dedent("""
            # Emotional Memory

            **ID:** EMOT-2025-12-20-001
            **Created:** 2025-12-20
            **Impact:** CRITICAL
            **Region:** AGENT
            **Confidence:** 1.0

            ## Raw Memory (Original)

            @Matt collaboration style and preferences.

            ## Compacted Memory (For Injection)
            ```
            ~EMOT:CRIT| @Matt { style: collaborative }
            ```
        """).strip()

        seed_file = tmp_path / "emotional_memory.md"
        seed_file.write_text(seed_content)

        result = import_seeds.parse_seed_file(seed_file)

        assert result is not None
        assert result["kind"] == MemoryKind.EMOTIONAL

    def test_parse_achievement_memory(self, tmp_path: Path) -> None:
        """Test parsing an achievement memory seed file."""
        seed_content = dedent("""
            # Achievement Memory

            **ID:** ACHV-2025-12-20-001
            **Created:** 2025-12-20
            **Impact:** HIGH
            **Region:** AGENT
            **Confidence:** 1.0

            ## Raw Memory (Original)

            Built LTM system in single session.

            ## Compacted Memory (For Injection)
            ```
            ~ACHV:HIGH| LTM v1.0 complete
            ```
        """).strip()

        seed_file = tmp_path / "achievement_memory.md"
        seed_file.write_text(seed_content)

        result = import_seeds.parse_seed_file(seed_file)

        assert result is not None
        assert result["kind"] == MemoryKind.ACHIEVEMENTS

    def test_parse_invalid_seed_file(self, tmp_path: Path) -> None:
        """Test parsing an invalid seed file returns None."""
        invalid_content = "This is not a valid seed file format."

        seed_file = tmp_path / "invalid.md"
        seed_file.write_text(invalid_content)

        result = import_seeds.parse_seed_file(seed_file)

        assert result is None

    def test_parse_missing_required_fields(self, tmp_path: Path) -> None:
        """Test parsing seed file with missing required fields."""
        incomplete_content = dedent("""
            # Incomplete Memory

            **ID:** LEARN-2025-12-20-001
            **Created:** 2025-12-20

            ## Raw Memory (Original)

            Some content.
        """).strip()

        seed_file = tmp_path / "incomplete.md"
        seed_file.write_text(incomplete_content)

        result = import_seeds.parse_seed_file(seed_file)

        assert result is None  # Missing impact and region


class TestImportRun:
    """Tests for the import run function."""

    def test_run_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test run with no arguments shows usage."""
        result = import_seeds.run([])
        captured = capsys.readouterr()

        assert result == 1
        assert "Usage:" in captured.out

    def test_run_nonexistent_directory(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test run with nonexistent directory."""
        result = import_seeds.run(["/nonexistent/path"])
        captured = capsys.readouterr()

        assert result == 1
        assert "not found" in captured.out

    def test_run_empty_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test run with empty directory."""
        result = import_seeds.run([str(tmp_path)])
        captured = capsys.readouterr()

        assert result == 1
        assert "No seed files found" in captured.out

    def test_run_skips_readme(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that README.md is skipped."""
        readme = tmp_path / "README.md"
        readme.write_text("# Seeds Directory\n\nThis is a readme.")

        result = import_seeds.run([str(tmp_path)])
        captured = capsys.readouterr()

        assert result == 1
        assert "No seed files found" in captured.out

    def test_run_imports_valid_seeds(self, tmp_path: Path, temp_db_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test importing valid seed files."""
        from unittest.mock import patch

        seed_content = dedent("""
            # Test Memory

            **ID:** LEARN-2025-12-20-001
            **Created:** 2025-12-20
            **Impact:** HIGH
            **Region:** AGENT
            **Confidence:** 1.0

            ## Raw Memory (Original)

            Test content for import.

            ## Compacted Memory (For Injection)
            ```
            ~LEARN:HIGH| Test content
            ```
        """).strip()

        seed_file = tmp_path / "test_seed.md"
        seed_file.write_text(seed_content)

        with patch("anima.tools.import_seeds.MemoryStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.get_memory.return_value = None  # Not already imported

            result = import_seeds.run([str(tmp_path)])
            captured = capsys.readouterr()

            assert result == 0
            assert "1 imported" in captured.out
            mock_store.save_memory.assert_called_once()

    def test_run_skips_already_imported(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that already imported seeds are skipped."""
        from unittest.mock import patch, MagicMock

        seed_content = dedent("""
            # Test Memory

            **ID:** LEARN-2025-12-20-001
            **Created:** 2025-12-20
            **Impact:** HIGH
            **Region:** AGENT
            **Confidence:** 1.0

            ## Raw Memory (Original)

            Test content.

            ## Compacted Memory (For Injection)
            ```
            ~LEARN:HIGH| Test
            ```
        """).strip()

        seed_file = tmp_path / "existing_seed.md"
        seed_file.write_text(seed_content)

        with patch("anima.tools.import_seeds.MemoryStore") as MockStore:
            mock_store = MockStore.return_value
            # Simulate already imported
            mock_store.get_memory.return_value = MagicMock()

            result = import_seeds.run([str(tmp_path)])
            captured = capsys.readouterr()

            assert result == 0
            assert "1 skipped" in captured.out
            mock_store.save_memory.assert_not_called()

    def test_run_strips_dsl_prefix(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Test that DSL prefix is stripped from compacted content."""
        from unittest.mock import patch

        seed_content = dedent("""
            # Test Memory

            **ID:** ARCH-2025-12-20-001
            **Created:** 2025-12-20
            **Impact:** CRITICAL
            **Region:** AGENT
            **Confidence:** 1.0

            ## Raw Memory (Original)

            Original content.

            ## Compacted Memory (For Injection)
            ```
            ~ARCH:CRIT| Architecture decision here
            ```
        """).strip()

        seed_file = tmp_path / "dsl_seed.md"
        seed_file.write_text(seed_content)

        with patch("anima.tools.import_seeds.MemoryStore") as MockStore:
            mock_store = MockStore.return_value
            mock_store.get_memory.return_value = None

            import_seeds.run([str(tmp_path)])

            # Check that the saved memory doesn't have DSL prefix
            call_args = mock_store.save_memory.call_args
            saved_memory = call_args[0][0]
            assert not saved_memory.content.startswith("~")
            assert "Architecture decision here" in saved_memory.content
