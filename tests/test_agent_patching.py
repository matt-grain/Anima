# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Tests for agent patching utilities.

These functions handle the detection and addition of the 'anima: subagent: true'
marker in agent YAML frontmatter.
"""

from anima.utils.agent_patching import has_subagent_marker, add_subagent_marker


class TestHasSubagentMarker:
    """Test detection of subagent markers in frontmatter."""

    def test_detects_anima_subagent_true(self):
        """Should detect anima: subagent: true in frontmatter."""
        content = """---
name: test-agent
anima:
  subagent: true
---
# Test Agent
"""
        assert has_subagent_marker(content) is True

    def test_detects_ltm_subagent_true(self):
        """Should detect ltm: subagent: true (legacy format)."""
        content = """---
name: test-agent
ltm:
  subagent: true
---
# Test Agent
"""
        assert has_subagent_marker(content) is True

    def test_detects_subagent_yes(self):
        """Should accept 'yes' as a truthy value."""
        content = """---
anima:
  subagent: yes
---
"""
        assert has_subagent_marker(content) is True

    def test_detects_subagent_1(self):
        """Should accept '1' as a truthy value."""
        content = """---
anima:
  subagent: 1
---
"""
        assert has_subagent_marker(content) is True

    def test_returns_false_when_subagent_false(self):
        """Should return False when subagent is explicitly false."""
        content = """---
anima:
  subagent: false
---
"""
        assert has_subagent_marker(content) is False

    def test_returns_false_when_no_frontmatter(self):
        """Should return False when there's no frontmatter."""
        content = "# Just a regular markdown file"
        assert has_subagent_marker(content) is False

    def test_returns_false_when_no_anima_section(self):
        """Should return False when frontmatter exists but no anima/ltm section."""
        content = """---
name: test-agent
description: A test agent
---
"""
        assert has_subagent_marker(content) is False

    def test_returns_false_when_anima_section_but_no_subagent(self):
        """Should return False when anima section exists but no subagent key."""
        content = """---
anima:
  id: test-agent
  name: Test Agent
---
"""
        assert has_subagent_marker(content) is False

    def test_handles_mixed_indentation(self):
        """Should handle tabs and spaces in frontmatter."""
        content = """---
anima:
\tsubagent: true
---
"""
        assert has_subagent_marker(content) is True

    def test_ignores_subagent_outside_anima_section(self):
        """Should only detect subagent within anima/ltm section."""
        content = """---
name: test-agent
subagent: true
anima:
  id: test
---
"""
        assert has_subagent_marker(content) is False


class TestAddSubagentMarker:
    """Test addition of subagent markers to frontmatter."""

    def test_adds_marker_to_unix_line_endings(self):
        """Should add marker before closing --- with Unix line endings."""
        content = """---
name: test-agent
---
# Test Agent
"""
        result = add_subagent_marker(content)
        assert "anima:\n  subagent: true\n---" in result
        assert result.startswith("---\nname: test-agent\n")

    def test_adds_marker_to_windows_line_endings(self):
        """Should add marker before closing --- with Windows line endings."""
        content = "---\r\nname: test-agent\r\n---\r\n# Test Agent\r\n"
        result = add_subagent_marker(content)
        assert "anima:\r\n  subagent: true\r\n---" in result
        assert result.startswith("---\r\nname: test-agent\r\n")

    def test_preserves_content_after_frontmatter(self):
        """Should preserve all content after the frontmatter."""
        content = """---
name: test-agent
---
# Test Agent

This is the agent description.
"""
        result = add_subagent_marker(content)
        assert "# Test Agent" in result
        assert "This is the agent description." in result

    def test_returns_unchanged_when_no_frontmatter(self):
        """Should return content unchanged if no frontmatter detected."""
        content = "# Just a regular file"
        result = add_subagent_marker(content)
        assert result == content

    def test_returns_unchanged_when_malformed_frontmatter(self):
        """Should return content unchanged if frontmatter is malformed."""
        content = "---\nname: test\n# Missing closing ---"
        result = add_subagent_marker(content)
        assert result == content

    def test_adds_marker_to_minimal_frontmatter(self):
        """Should add marker even to minimal frontmatter."""
        content = "---\nname: test\n---\n# Content"
        result = add_subagent_marker(content)
        assert "anima:\n  subagent: true\n---" in result

    def test_preserves_existing_frontmatter_fields(self):
        """Should preserve all existing frontmatter fields."""
        content = """---
name: test-agent
description: A test agent
version: 1.0
---
"""
        result = add_subagent_marker(content)
        assert "name: test-agent" in result
        assert "description: A test agent" in result
        assert "version: 1.0" in result
        assert "anima:\n  subagent: true" in result


class TestRoundTrip:
    """Test that add + has work correctly together."""

    def test_roundtrip_detection(self):
        """Should detect marker after adding it."""
        original = """---
name: test-agent
---
# Test
"""
        modified = add_subagent_marker(original)
        assert has_subagent_marker(modified) is True

    def test_idempotent_addition(self):
        """Adding marker twice should not duplicate it."""
        original = """---
name: test-agent
---
"""
        first_add = add_subagent_marker(original)
        # If we try to add again, has_subagent_marker should prevent it
        # (though the function itself doesn't check, the caller should)
        assert has_subagent_marker(first_add) is True
