"""Command registry and base command for the interactive console."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .parser import ParsedCommand

if TYPE_CHECKING:
    from .app import ConsoleApp

logger = logging.getLogger(__name__)


@dataclass
class CommandInfo:
    """Metadata about a registered command."""

    name: str
    description: str
    subcommands: dict[str, str] = field(default_factory=dict)  # subcommand -> description
    category: str = "General"


class BaseCommand(ABC):
    """Base class for all console commands."""

    # Subclasses must define these
    name: str = ""
    description: str = ""
    category: str = "General"
    subcommands: dict[str, str] = {}  # subcommand -> description

    def __init__(self, app: ConsoleApp):
        self.app = app

    @abstractmethod
    def execute(self, cmd: ParsedCommand) -> None:
        """Execute the command."""
        ...

    def get_info(self) -> CommandInfo:
        return CommandInfo(
            name=self.name,
            description=self.description,
            subcommands=dict(self.subcommands),
            category=self.category,
        )


class CommandRegistry:
    """Registry for console commands."""

    def __init__(self) -> None:
        self._commands: dict[str, BaseCommand] = {}

    def register(self, command: BaseCommand) -> None:
        """Register a command instance."""
        self._commands[command.name] = command

    def get(self, name: str) -> BaseCommand | None:
        """Get a command by name."""
        return self._commands.get(name)

    def dispatch(self, cmd: ParsedCommand) -> bool:
        """
        Dispatch a parsed command.

        Returns True if command was found, False otherwise.
        """
        command = self._commands.get(cmd.command)
        if command is None:
            return False
        try:
            command.execute(cmd)
        except Exception as e:
            logger.error(f"Command error: {e}")
            from rich.console import Console

            Console().print(f"[red]Error: {e}[/red]")
        return True

    def all_commands(self) -> dict[str, BaseCommand]:
        """Get all registered commands."""
        return dict(self._commands)

    def get_completions(self) -> list[str]:
        """Get all command names for tab completion."""
        return [f"/{name}" for name in self._commands]

    def get_subcommand_completions(self, command_name: str) -> list[str]:
        """Get subcommand names for a command."""
        cmd = self._commands.get(command_name)
        if cmd and cmd.subcommands:
            return list(cmd.subcommands.keys())
        return []
