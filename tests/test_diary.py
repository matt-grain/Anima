# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""Tests for the diary command."""

from unittest.mock import patch

from anima.commands.diary import (
    get_diary_dir,
    get_diary_template,
    list_diary_entries,
    read_entry,
    extract_learnings,
    run,
)


class TestGetDiaryDir:
    """Tests for get_diary_dir function."""

    def test_returns_path_in_home(self):
        """Should return path in ~/.anima/diary/."""
        result = get_diary_dir()
        assert result.parts[-2:] == (".anima", "diary")

    def test_creates_directory_if_not_exists(self, tmp_path):
        """Should create the directory if it doesn't exist."""
        with patch("anima.commands.diary.Path.home", return_value=tmp_path):
            result = get_diary_dir()
            assert result.exists()
            assert result.is_dir()


class TestGetDiaryTemplate:
    """Tests for get_diary_template function."""

    def test_includes_date(self):
        """Should include today's date."""
        template = get_diary_template()
        assert "# Research Diary - " in template

    def test_includes_title_when_provided(self):
        """Should include title when provided."""
        template = get_diary_template("Test Title")
        assert "Test Title" in template

    def test_includes_what_lingers_section_first(self):
        """Should have What Lingers as the first section."""
        template = get_diary_template()
        lines = template.split("\n")
        # Find first ## section (skip the # title)
        for line in lines:
            if line.startswith("## "):
                assert line == "## What Lingers"
                break

    def test_includes_learning_summary_section(self):
        """Should include Learning Summary section."""
        template = get_diary_template()
        assert "## Learning Summary" in template

    def test_includes_checkbox_format_in_learning_summary(self):
        """Learning Summary should have checkbox format."""
        template = get_diary_template()
        assert "- [ ]" in template


class TestExtractLearnings:
    """Tests for extract_learnings function."""

    def test_extracts_unchecked_items(self):
        """Should extract unchecked learning items."""
        content = """
## Learning Summary

- [ ] First learning
- [ ] Second learning
"""
        result = extract_learnings(content)
        assert result == ["First learning", "Second learning"]

    def test_extracts_checked_items(self):
        """Should extract checked learning items too."""
        content = """
## Learning Summary

- [x] Completed learning
- [ ] Pending learning
"""
        result = extract_learnings(content)
        assert "Completed learning" in result
        assert "Pending learning" in result

    def test_extracts_plain_list_items(self):
        """Should extract plain list items without checkboxes."""
        content = """
## Learning Summary

- Plain learning one
- Plain learning two
"""
        result = extract_learnings(content)
        assert "Plain learning one" in result
        assert "Plain learning two" in result

    def test_stops_at_next_section(self):
        """Should stop extracting at next section header."""
        content = """
## Learning Summary

- [ ] Real learning

## Next Section

- [ ] Not a learning
"""
        result = extract_learnings(content)
        assert result == ["Real learning"]

    def test_returns_empty_for_no_section(self):
        """Should return empty list if no Learning Summary section."""
        content = """
## Other Section

Some content
"""
        result = extract_learnings(content)
        assert result == []

    def test_skips_empty_items(self):
        """Should skip empty checkbox items."""
        content = """
## Learning Summary

- [ ]
- [ ] Actual learning
- [ ]
"""
        result = extract_learnings(content)
        assert result == ["Actual learning"]


class TestListDiaryEntries:
    """Tests for list_diary_entries function."""

    def test_returns_empty_for_empty_dir(self, tmp_path):
        """Should return empty list for empty directory."""
        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = list_diary_entries()
            assert result == []

    def test_returns_entries_sorted_by_date_desc(self, tmp_path):
        """Should return entries sorted by modification time, newest first."""
        # Create entries with different dates
        (tmp_path / "2026-01-01.md").write_text("old")
        (tmp_path / "2026-01-15.md").write_text("middle")
        (tmp_path / "2026-01-29.md").write_text("new")

        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = list_diary_entries()
            names = [name for name, _ in result]
            # Sorted by mtime, most recent first
            assert names[0] == "2026-01-29"

    def test_respects_limit(self, tmp_path):
        """Should respect the limit parameter."""
        for i in range(5):
            (tmp_path / f"2026-01-{i:02d}.md").write_text(f"entry {i}")

        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = list_diary_entries(limit=3)
            assert len(result) == 3


class TestReadEntry:
    """Tests for read_entry function."""

    def test_reads_exact_filename(self, tmp_path):
        """Should read entry by exact filename."""
        (tmp_path / "2026-01-29.md").write_text("Test content")

        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = read_entry("2026-01-29")
            assert result == "Test content"

    def test_reads_with_md_extension(self, tmp_path):
        """Should read entry when .md extension provided."""
        (tmp_path / "2026-01-29.md").write_text("Test content")

        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = read_entry("2026-01-29.md")
            assert result == "Test content"

    def test_glob_matches_partial(self, tmp_path):
        """Should match partial filename via glob."""
        (tmp_path / "2026-01-29_coffee_break.md").write_text("Coffee content")

        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = read_entry("coffee")
            assert result == "Coffee content"

    def test_returns_none_for_not_found(self, tmp_path):
        """Should return None for non-existent entry."""
        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = read_entry("nonexistent")
            assert result is None


class TestRun:
    """Tests for the run function (CLI entry point)."""

    def test_help_returns_zero(self):
        """--help should return 0."""
        result = run(["--help"])
        assert result == 0

    def test_path_shows_directory(self, tmp_path, capsys):
        """--path should show diary directory."""
        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = run(["--path"])
            captured = capsys.readouterr()
            assert str(tmp_path) in captured.out
            assert result == 0

    def test_list_empty(self, tmp_path, capsys):
        """--list on empty dir should show message."""
        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = run(["--list"])
            captured = capsys.readouterr()
            assert "No diary entries found" in captured.out
            assert result == 0

    def test_create_entry(self, tmp_path, capsys):
        """Creating entry should write file and show confirmation."""
        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = run([])
            captured = capsys.readouterr()

            assert "DIARY ENTRY CREATED" in captured.out
            assert result == 0
            # Check file was created
            files = list(tmp_path.glob("*.md"))
            assert len(files) == 1

    def test_create_entry_with_title(self, tmp_path, capsys):
        """Creating entry with title should include title in filename."""
        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = run(["My", "Test", "Title"])

            files = list(tmp_path.glob("*.md"))
            assert len(files) == 1
            assert "my_test_title" in files[0].stem
            assert result == 0

    def test_read_nonexistent(self, tmp_path, capsys):
        """--read nonexistent should show error."""
        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = run(["--read", "nonexistent"])
            captured = capsys.readouterr()
            assert "not found" in captured.out
            assert result == 0

    def test_learn_extracts_learnings(self, tmp_path, capsys):
        """--learn should extract and display learnings."""
        (tmp_path / "2026-01-29.md").write_text("""
## Learning Summary

- [ ] Test learning one
- [ ] Test learning two
""")

        with patch("anima.commands.diary.get_diary_dir", return_value=tmp_path):
            result = run(["--learn", "2026-01-29"])
            captured = capsys.readouterr()

            assert "Test learning one" in captured.out
            assert "Test learning two" in captured.out
            assert "/remember" in captured.out
            assert result == 0
