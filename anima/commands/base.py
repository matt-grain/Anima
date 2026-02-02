# MIT License
# Copyright (c) 2025 Matt / Grain Ecosystem

"""
Base class for LTM CLI commands.

Provides standardized argument parsing, agent/project resolution,
and dependency injection for improved consistency and testability.
"""

from abc import ABC, abstractmethod
from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import Optional

from anima.core import AgentResolver, Agent, Project
from anima.storage import MemoryStoreProtocol, MemoryStore


class BaseCommand(ABC):
    """
    Base class for LTM CLI commands.

    Provides common functionality for agent/project resolution,
    store initialization, and argument parsing.

    Usage:
        class MyCommand(BaseCommand):
            name = "my-command"
            description = "Does something useful"

            def configure_parser(self, parser: ArgumentParser) -> None:
                parser.add_argument("--flag", action="store_true")

            def execute(self, args: Namespace) -> int:
                # Implementation here
                return 0

        # Entry point for CLI
        def run(args: list[str]) -> int:
            return MyCommand().run(args)
    """

    name: str
    description: str

    def __init__(
        self,
        store: Optional[MemoryStoreProtocol] = None,
        project_path: Optional[Path] = None,
    ):
        """
        Initialize the command.

        Args:
            store: Optional MemoryStore instance (for testing)
            project_path: Optional project path override
        """
        self._store = store
        self._resolver = AgentResolver(project_path or Path.cwd())
        self._agent: Optional[Agent] = None
        self._project: Optional[Project] = None

    @property
    def store(self) -> MemoryStoreProtocol:
        """Lazily initialize the memory store."""
        if self._store is None:
            self._store = MemoryStore()
        return self._store

    @property
    def agent(self) -> Agent:
        """Lazily resolve the current agent."""
        if self._agent is None:
            self._agent = self._resolver.resolve()
        return self._agent

    @property
    def project(self) -> Project:
        """Lazily resolve the current project."""
        if self._project is None:
            self._project = self._resolver.resolve_project()
        return self._project

    def ensure_context_saved(self) -> None:
        """Ensure agent and project are persisted to the store."""
        self.store.save_agent(self.agent)
        self.store.save_project(self.project)

    @abstractmethod
    def configure_parser(self, parser: ArgumentParser) -> None:
        """
        Configure command-specific arguments.

        Args:
            parser: The ArgumentParser to configure
        """
        pass

    @abstractmethod
    def execute(self, args: Namespace) -> int:
        """
        Execute the command with parsed arguments.

        Args:
            args: Parsed command-line arguments

        Returns:
            Exit code (0 for success)
        """
        pass

    def run(self, argv: list[str]) -> int:
        """
        Parse arguments and execute command.

        Args:
            argv: Command-line arguments (without command name)

        Returns:
            Exit code (0 for success)
        """
        parser = ArgumentParser(prog=f"uv run anima {self.name}", description=self.description)
        self.configure_parser(parser)

        try:
            args = parser.parse_args(argv)
        except SystemExit as e:
            # argparse calls sys.exit on --help or error
            return e.code if isinstance(e.code, int) else 0

        return self.execute(args)
