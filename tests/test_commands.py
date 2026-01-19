# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Unit tests for LTM commands.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from anima.core import Agent, Memory, MemoryKind, Project, RegionType, ImpactLevel
from anima.commands import (
    remember, recall, forget, memories, stats, graph,
    export_memories, import_memories
)


class TestRememberCommand:
    """Tests for the remember command."""

    def test_remember_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test remember with no arguments."""
        result = remember.run([])
        captured = capsys.readouterr()

        assert result == 1  # Error code
        assert "Usage:" in captured.out

    def test_remember_success(
        self, temp_db_path: Path, temp_project_dir: Path
    ) -> None:
        """Test successful memory creation."""
        with patch("anima.commands.remember.MemoryStore") as MockStore, \
             patch("anima.commands.remember.AgentResolver") as MockResolver:

            # Setup mocks
            mock_store = MagicMock()
            mock_store.get_latest_memory_of_kind.return_value = None
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            result = remember.run(["Test memory content"])

            assert result == 0
            mock_store.save_memory.assert_called_once()

    def test_remember_infers_critical_impact(
        self, temp_db_path: Path, temp_project_dir: Path
    ) -> None:
        """Test remember infers CRITICAL impact from keywords."""
        with patch("anima.commands.remember.MemoryStore") as MockStore, \
             patch("anima.commands.remember.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            mock_store.get_latest_memory_of_kind.return_value = None
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # "never" triggers CRITICAL impact
            result = remember.run(["Never use print for logging"])

            assert result == 0
            call_args = mock_store.save_memory.call_args
            saved_memory = call_args[0][0]
            assert saved_memory.impact == ImpactLevel.CRITICAL

    def test_remember_infers_architectural_kind(
        self, temp_db_path: Path, temp_project_dir: Path
    ) -> None:
        """Test remember infers ARCHITECTURAL kind from keywords."""
        with patch("anima.commands.remember.MemoryStore") as MockStore, \
             patch("anima.commands.remember.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            mock_store.get_latest_memory_of_kind.return_value = None
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # "architecture" triggers ARCHITECTURAL kind
            result = remember.run(["Use layered architecture pattern"])

            assert result == 0
            call_args = mock_store.save_memory.call_args
            saved_memory = call_args[0][0]
            assert saved_memory.kind == MemoryKind.ARCHITECTURAL

    def test_remember_explicit_region_flag(
        self, temp_db_path: Path, temp_project_dir: Path
    ) -> None:
        """Test remember with explicit --region agent flag."""
        with patch("anima.commands.remember.MemoryStore") as MockStore, \
             patch("anima.commands.remember.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            mock_store.get_latest_memory_of_kind.return_value = None
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # Explicit --region agent should override default PROJECT inference
            result = remember.run(["--region", "agent", "This is a test memory"])

            assert result == 0
            call_args = mock_store.save_memory.call_args
            saved_memory = call_args[0][0]
            assert saved_memory.region == RegionType.AGENT

    def test_remember_explicit_kind_and_impact_flags(
        self, temp_db_path: Path, temp_project_dir: Path
    ) -> None:
        """Test remember with explicit --kind and --impact flags."""
        with patch("anima.commands.remember.MemoryStore") as MockStore, \
             patch("anima.commands.remember.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            mock_store.get_latest_memory_of_kind.return_value = None
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # Explicit flags should override inference
            result = remember.run([
                "--kind", "achievements",
                "--impact", "critical",
                "Some test content"
            ])

            assert result == 0
            call_args = mock_store.save_memory.call_args
            saved_memory = call_args[0][0]
            assert saved_memory.kind == MemoryKind.ACHIEVEMENTS
            assert saved_memory.impact == ImpactLevel.CRITICAL

    def test_remember_help_flag(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test remember --help shows usage."""
        result = remember.run(["--help"])
        captured = capsys.readouterr()

        assert result == 0
        assert "region" in captured.out.lower() or "usage" in captured.out.lower()

    def test_remember_project_flag_matching(
        self, temp_db_path: Path, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test remember with --project flag matching current project succeeds."""
        with patch("anima.commands.remember.MemoryStore") as MockStore,              patch("anima.commands.remember.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            mock_store.get_latest_memory_of_kind.return_value = None
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="TestProject", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # --project matches resolved project name
            result = remember.run(["--project", "TestProject", "Test memory content"])

            assert result == 0
            mock_store.save_memory.assert_called_once()

    def test_remember_project_flag_mismatch(
        self, temp_db_path: Path, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test remember with --project flag not matching current project fails."""
        with patch("anima.commands.remember.MemoryStore") as MockStore,              patch("anima.commands.remember.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="TestProject", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # --project does NOT match resolved project name
            result = remember.run(["--project", "WrongProject", "Test memory content"])
            captured = capsys.readouterr()

            assert result == 1
            assert "ERROR" in captured.out
            assert "WrongProject" in captured.out
            assert "TestProject" in captured.out
            assert "does not match" in captured.out
            # Should NOT have saved anything
            mock_store.save_memory.assert_not_called()

    def test_remember_project_flag_case_sensitive(
        self, temp_db_path: Path, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test --project flag is case-sensitive."""
        with patch("anima.commands.remember.MemoryStore") as MockStore,              patch("anima.commands.remember.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="TestProject", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # Wrong case should fail
            result = remember.run(["--project", "testproject", "Test memory content"])
            captured = capsys.readouterr()

            assert result == 1
            assert "ERROR" in captured.out
            mock_store.save_memory.assert_not_called()



class TestRecallCommand:
    """Tests for the recall command."""

    def test_recall_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test recall with no arguments."""
        result = recall.run([])
        captured = capsys.readouterr()

        assert result == 1
        assert "Usage:" in captured.out

    def test_recall_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test recall help."""
        result = recall.run(["--help"])
        captured = capsys.readouterr()

        assert result == 0
        assert "Usage:" in captured.out
        assert "--full" in captured.out

    def test_recall_success(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test successful recall."""
        with patch("anima.commands.recall.MemoryStore") as MockStore, \
             patch("anima.commands.recall.AgentResolver") as MockResolver, \
             patch("anima.commands.recall.Path") as MockPath:

            mock_store = MagicMock()
            mock_memory = Memory(
                agent_id="test",
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Always use pytest",
                impact=ImpactLevel.MEDIUM
            )
            mock_store.search_memories.return_value = [mock_memory]
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = recall.run(["pytest"])
            captured = capsys.readouterr()

            assert result == 0
            assert "Found 1 memories" in captured.out
            assert "pytest" in captured.out

    def test_recall_no_matches(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test recall with no matches."""
        with patch("anima.commands.recall.MemoryStore") as MockStore, \
             patch("anima.commands.recall.AgentResolver") as MockResolver, \
             patch("anima.commands.recall.Path") as MockPath:

            mock_store = MagicMock()
            mock_store.search_memories.return_value = []
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = recall.run(["nonexistent"])
            captured = capsys.readouterr()

            assert result == 0
            assert "No memories found" in captured.out

    def test_recall_with_full_flag(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test recall with --full flag."""
        with patch("anima.commands.recall.MemoryStore") as MockStore, \
             patch("anima.commands.recall.AgentResolver") as MockResolver, \
             patch("anima.commands.recall.Path") as MockPath:

            mock_store = MagicMock()
            mock_memory = Memory(
                agent_id="test",
                region=RegionType.AGENT,
                kind=MemoryKind.EMOTIONAL,
                content="@Matt { style: collaborative; likes: humor; }",
                impact=ImpactLevel.CRITICAL
            )
            mock_store.search_memories.return_value = [mock_memory]
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = recall.run(["--full", "Matt"])
            captured = capsys.readouterr()

            assert result == 0
            assert "Region:" in captured.out
            assert "Content:" in captured.out


class TestForgetCommand:
    """Tests for the forget command."""

    def test_forget_no_args(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test forget with no arguments."""
        result = forget.run([])
        captured = capsys.readouterr()

        assert result == 1
        assert "Usage:" in captured.out

    def test_forget_memory_not_found(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test forget with non-existent memory."""
        with patch("anima.commands.forget.MemoryStore") as MockStore, \
             patch("anima.commands.forget.AgentResolver") as MockResolver:

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = []  # No memories found
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            MockResolver.return_value = mock_resolver

            result = forget.run(["nonexistent-id"])
            captured = capsys.readouterr()

            assert result == 1
            assert "not found" in captured.out.lower() or "no memory" in captured.out.lower()


class TestMemoriesCommand:
    """Tests for the memories command."""

    def test_memories_empty(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test memories with no memories."""
        with patch("anima.commands.memories.MemoryStore") as MockStore, \
             patch("anima.commands.memories.AgentResolver") as MockResolver, \
             patch("anima.commands.memories.Path") as MockPath:

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = []
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = memories.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "No memories found" in captured.out

    def test_memories_with_data(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test memories with data."""
        with patch("anima.commands.memories.MemoryStore") as MockStore, \
             patch("anima.commands.memories.AgentResolver") as MockResolver, \
             patch("anima.commands.memories.Path") as MockPath:

            mock_store = MagicMock()
            mock_memories = [
                Memory(
                    agent_id="test",
                    region=RegionType.AGENT,
                    kind=MemoryKind.EMOTIONAL,
                    content="@Matt collaborative",
                    impact=ImpactLevel.CRITICAL
                ),
                Memory(
                    agent_id="test",
                    region=RegionType.PROJECT,
                    project_id="test-proj",
                    kind=MemoryKind.ARCHITECTURAL,
                    content="Use pytest",
                    impact=ImpactLevel.HIGH
                ),
            ]
            mock_store.get_memories_for_agent.return_value = mock_memories
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test Agent", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test Project", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = memories.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "Memories for Test Agent" in captured.out
            assert "EMOTIONAL" in captured.out
            assert "ARCHITECTURAL" in captured.out
            assert "Total: 2 memories" in captured.out

    def test_memories_filter_by_kind(
        self, temp_project_dir: Path
    ) -> None:
        """Test memories with kind filter."""
        with patch("anima.commands.memories.MemoryStore") as MockStore, \
             patch("anima.commands.memories.AgentResolver") as MockResolver, \
             patch("anima.commands.memories.Path") as MockPath:

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = []
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            memories.run(["--kind", "EMOTIONAL"])

            # Verify the filter was passed
            call_args = mock_store.get_memories_for_agent.call_args
            assert call_args[1]["kind"] == MemoryKind.EMOTIONAL


class TestStatsCommand:
    """Tests for the memory-stats command."""

    def test_stats_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test stats --help shows usage."""
        result = stats.run(["--help"])
        captured = capsys.readouterr()

        assert result == 0
        assert "Usage:" in captured.out

    def test_stats_empty(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test stats with no memories."""
        with patch("anima.commands.stats.MemoryStore") as MockStore, \
             patch("anima.commands.stats.AgentResolver") as MockResolver, \
             patch("anima.commands.stats.Path") as MockPath:

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = []
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = stats.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "No memories found" in captured.out

    def test_stats_with_data(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test stats with memories."""
        with patch("anima.commands.stats.MemoryStore") as MockStore, \
             patch("anima.commands.stats.AgentResolver") as MockResolver, \
             patch("anima.commands.stats.Path") as MockPath:

            mock_store = MagicMock()
            mock_memories = [
                Memory(
                    agent_id="test",
                    region=RegionType.AGENT,
                    kind=MemoryKind.EMOTIONAL,
                    content="@Matt collaborative",
                    impact=ImpactLevel.CRITICAL
                ),
                Memory(
                    agent_id="test",
                    region=RegionType.PROJECT,
                    project_id="test-proj",
                    kind=MemoryKind.LEARNINGS,
                    content="Use pytest",
                    impact=ImpactLevel.MEDIUM
                ),
            ]
            mock_store.get_memories_for_agent.return_value = mock_memories
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test Agent", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = stats.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "Memory Statistics" in captured.out
            assert "Total Memories:** 2" in captured.out
            assert "By Region" in captured.out
            assert "By Kind" in captured.out
            assert "By Impact" in captured.out
            assert "Health" in captured.out


class TestGraphCommand:
    """Tests for the memory-graph command."""

    def test_graph_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test graph --help shows usage."""
        result = graph.run(["--help"])
        captured = capsys.readouterr()

        assert result == 0
        assert "Usage:" in captured.out
        assert "--all" in captured.out

    def test_graph_empty(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test graph with no memories."""
        with patch("anima.commands.graph.MemoryStore") as MockStore, \
             patch("anima.commands.graph.AgentResolver") as MockResolver, \
             patch("anima.commands.graph.Path") as MockPath:

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = []
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = graph.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "No memories found" in captured.out

    def test_graph_with_chain(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test graph with a memory chain."""
        with patch("anima.commands.graph.MemoryStore") as MockStore, \
             patch("anima.commands.graph.AgentResolver") as MockResolver, \
             patch("anima.commands.graph.Path") as MockPath:

            # Create a chain: mem1 -> mem2 (mem1 superseded by mem2)
            mem1 = Memory(
                id="mem-001",
                agent_id="test",
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Original learning",
                impact=ImpactLevel.MEDIUM,
                superseded_by="mem-002"
            )
            mem2 = Memory(
                id="mem-002",
                agent_id="test",
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Updated learning",
                impact=ImpactLevel.MEDIUM,
                previous_memory_id="mem-001"
            )

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = [mem1, mem2]
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test Agent", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = graph.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "Memory Graph" in captured.out
            assert "Chains" in captured.out
            assert "In chains: 2" in captured.out

    def test_graph_standalone_hidden_by_default(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test that standalone memories are hidden without --all."""
        with patch("anima.commands.graph.MemoryStore") as MockStore, \
             patch("anima.commands.graph.AgentResolver") as MockResolver, \
             patch("anima.commands.graph.Path") as MockPath:

            # Single standalone memory
            mem = Memory(
                id="mem-001",
                agent_id="test",
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Standalone learning",
                impact=ImpactLevel.MEDIUM
            )

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = [mem]
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = graph.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "Standalone: 1" in captured.out
            assert "Use --all to show" in captured.out

    def test_graph_with_all_flag(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test graph with --all shows standalone memories."""
        with patch("anima.commands.graph.MemoryStore") as MockStore, \
             patch("anima.commands.graph.AgentResolver") as MockResolver, \
             patch("anima.commands.graph.Path") as MockPath:

            mem = Memory(
                id="mem-001",
                agent_id="test",
                region=RegionType.AGENT,
                kind=MemoryKind.LEARNINGS,
                content="Standalone learning",
                impact=ImpactLevel.MEDIUM
            )

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = [mem]
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = graph.run(["--all"])
            captured = capsys.readouterr()

            assert result == 0
            assert "Standalone" in captured.out
            assert "mem-001" in captured.out


class TestExportCommand:
    """Tests for the memory-export command."""

    def test_export_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test export --help shows usage."""
        result = export_memories.run(["--help"])
        captured = capsys.readouterr()

        assert result == 0
        assert "Usage:" in captured.out
        assert "--agent-only" in captured.out

    def test_export_empty(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test export with no memories."""
        with patch("anima.commands.export_memories.MemoryStore") as MockStore, \
             patch("anima.commands.export_memories.AgentResolver") as MockResolver, \
             patch("anima.commands.export_memories.Path") as MockPath:

            mock_store = MagicMock()
            mock_store.get_memories_for_agent.return_value = []
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = export_memories.run([])
            captured = capsys.readouterr()

            assert result == 0
            assert "No memories to export" in captured.err

    def test_export_to_stdout(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test export to stdout as JSON."""
        import json

        with patch("anima.commands.export_memories.MemoryStore") as MockStore, \
             patch("anima.commands.export_memories.AgentResolver") as MockResolver, \
             patch("anima.commands.export_memories.Path") as MockPath:

            mock_store = MagicMock()
            mock_memories = [
                Memory(
                    id="mem-001",
                    agent_id="test",
                    region=RegionType.AGENT,
                    kind=MemoryKind.LEARNINGS,
                    content="Test learning",
                    impact=ImpactLevel.MEDIUM
                ),
            ]
            mock_store.get_memories_for_agent.return_value = mock_memories
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test Agent", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = export_memories.run([])
            captured = capsys.readouterr()

            assert result == 0
            # Should be valid JSON
            data = json.loads(captured.out)
            assert data["version"] == "1.0"
            assert len(data["memories"]) == 1
            assert data["memories"][0]["content"] == "Test learning"

    def test_export_agent_only_filter(
        self, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test export with --agent-only filter."""
        import json

        with patch("anima.commands.export_memories.MemoryStore") as MockStore, \
             patch("anima.commands.export_memories.AgentResolver") as MockResolver, \
             patch("anima.commands.export_memories.Path") as MockPath:

            mock_store = MagicMock()
            mock_memories = [
                Memory(
                    id="mem-001",
                    agent_id="test",
                    region=RegionType.AGENT,
                    kind=MemoryKind.LEARNINGS,
                    content="Agent learning",
                    impact=ImpactLevel.MEDIUM
                ),
                Memory(
                    id="mem-002",
                    agent_id="test",
                    region=RegionType.PROJECT,
                    project_id="test-proj",
                    kind=MemoryKind.LEARNINGS,
                    content="Project learning",
                    impact=ImpactLevel.MEDIUM
                ),
            ]
            mock_store.get_memories_for_agent.return_value = mock_memories
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir

            result = export_memories.run(["--agent-only"])
            captured = capsys.readouterr()

            assert result == 0
            data = json.loads(captured.out)
            assert len(data["memories"]) == 1
            assert data["memories"][0]["region"] == "AGENT"


class TestImportCommand:
    """Tests for the memory-import command."""

    def test_import_help(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test import --help shows usage."""
        result = import_memories.run(["--help"])
        captured = capsys.readouterr()

        assert result == 0
        assert "Usage:" in captured.out
        assert "--dry-run" in captured.out

    def test_import_no_file(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test import without file argument."""
        result = import_memories.run([])
        captured = capsys.readouterr()

        assert result == 1
        assert "Usage:" in captured.out

    def test_import_file_not_found(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test import with non-existent file."""
        result = import_memories.run(["/nonexistent/file.json"])
        captured = capsys.readouterr()

        assert result == 1
        assert "not found" in captured.out

    def test_import_dry_run(
        self, tmp_path: Path, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test import with --dry-run."""
        import json

        # Create test export file
        export_data = {
            "version": "1.0",
            "memories": [
                {
                    "id": "mem-001",
                    "region": "AGENT",
                    "kind": "LEARNINGS",
                    "content": "Test learning",
                    "impact": "MEDIUM",
                    "confidence": 1.0,
                    "created_at": "2025-12-20T10:00:00",
                }
            ]
        }
        export_file = tmp_path / "test_export.json"
        export_file.write_text(json.dumps(export_data))

        with patch("anima.commands.import_memories.MemoryStore") as MockStore, \
             patch("anima.commands.import_memories.AgentResolver") as MockResolver, \
             patch("anima.commands.import_memories.Path") as MockPath:

            mock_store = MagicMock()
            mock_store.get_memory.return_value = None  # Not already imported
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            # Mock Path but preserve real file operations
            MockPath.cwd.return_value = temp_project_dir
            MockPath.return_value.exists.return_value = True
            MockPath.return_value.read_text.return_value = export_file.read_text()

            result = import_memories.run([str(export_file), "--dry-run"])
            captured = capsys.readouterr()

            assert result == 0
            assert "Would import" in captured.out
            assert "Dry run complete" in captured.out
            # Should not have saved anything
            mock_store.save_memory.assert_not_called()

    def test_import_merge_skips_existing(
        self, tmp_path: Path, temp_project_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test import with --merge skips existing memories."""
        import json

        export_data = {
            "version": "1.0",
            "memories": [
                {
                    "id": "existing-mem",
                    "region": "AGENT",
                    "kind": "LEARNINGS",
                    "content": "Already exists",
                    "impact": "MEDIUM",
                    "confidence": 1.0,
                    "created_at": "2025-12-20T10:00:00",
                }
            ]
        }
        export_file = tmp_path / "test_export.json"
        export_file.write_text(json.dumps(export_data))

        with patch("anima.commands.import_memories.MemoryStore") as MockStore, \
             patch("anima.commands.import_memories.AgentResolver") as MockResolver, \
             patch("anima.commands.import_memories.Path") as MockPath:

            mock_store = MagicMock()
            # Simulate existing memory
            mock_store.get_memory.return_value = MagicMock()
            MockStore.return_value = mock_store

            mock_agent = Agent(id="test", name="Test", definition_path=None, signing_key=None)
            mock_project = Project(id="test-proj", name="Test", path=temp_project_dir)

            mock_resolver = MagicMock()
            mock_resolver.resolve.return_value = mock_agent
            mock_resolver.resolve_project.return_value = mock_project
            MockResolver.return_value = mock_resolver

            MockPath.cwd.return_value = temp_project_dir
            MockPath.return_value.exists.return_value = True
            MockPath.return_value.read_text.return_value = export_file.read_text()

            result = import_memories.run([str(export_file), "--merge"])
            captured = capsys.readouterr()

            assert result == 0
            assert "1 skipped" in captured.out
