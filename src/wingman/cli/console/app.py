"""Main REPL loop for the Wingman interactive console."""

from __future__ import annotations

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console

from wingman import __version__
from wingman.config.paths import WingmanPaths
from wingman.config.settings import Settings

from .command_registry import CommandRegistry
from .completer import ConsoleCompleter
from .parser import parse_input

console = Console()


class ConsoleApp:
    """Interactive console application."""

    def __init__(self) -> None:
        self.paths = WingmanPaths()
        self.paths.ensure_directories()
        self.registry = CommandRegistry()
        self._running = True

        # Load settings if config exists
        self.settings: Settings | None = None
        if self.paths.config_exists():
            try:
                self.settings = Settings.load(paths=self.paths)
            except Exception:
                pass

        # RPC client (lazy-initialized when needed)
        self._rpc_client = None

        # Register all commands
        self._register_commands()

    @property
    def rpc(self):
        """Lazy-initialize RPC client."""
        if self._rpc_client is None:
            from wingman.core.rpc_client import RPCClient

            self._rpc_client = RPCClient(self.paths.rpc_socket)
        return self._rpc_client

    def _register_commands(self) -> None:
        """Register all console commands."""
        from .commands.bot import (
            BotCommand,
            PauseCommand,
            RestartCommand,
            ResumeCommand,
            StatusCommand,
            StopCommand,
        )
        from .commands.config import ConfigCommand
        from .commands.contacts import ContactsCommand
        from .commands.groups import GroupsCommand
        from .commands.help import HelpCommand, QuitCommand
        from .commands.history import ChatsCommand, HistoryCommand
        from .commands.logs import LogsCommand
        from .commands.policies import PoliciesCommand
        from .commands.send import SendCommand
        from .commands.stats import ActivityCommand, StatsCommand

        for cmd_class in [
            HelpCommand,
            QuitCommand,
            BotCommand,
            StopCommand,
            RestartCommand,
            StatusCommand,
            PauseCommand,
            ResumeCommand,
            ConfigCommand,
            ContactsCommand,
            GroupsCommand,
            PoliciesCommand,
            SendCommand,
            ChatsCommand,
            HistoryCommand,
            LogsCommand,
            StatsCommand,
            ActivityCommand,
        ]:
            self.registry.register(cmd_class(self))

    def _print_banner(self) -> None:
        """Print the welcome banner."""
        bot_name = self.settings.bot_name if self.settings else "Wingman"
        model = self.settings.openai_model if self.settings else "not configured"

        # Check daemon status
        from wingman.daemon import DaemonManager

        daemon = DaemonManager(self.paths)
        if daemon.is_running():
            pid = daemon.get_pid()
            status = f"[green]Running[/green] (PID {pid})"
        else:
            status = "[dim]Not running[/dim]"

        console.print()
        console.print(f"  [bold blue]Wingman[/bold blue] v{__version__}")
        console.print()
        console.print(f"  Bot: [bold]{bot_name}[/bold] | Model: {model} | Status: {status}")
        console.print()
        console.print("  Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit.")
        console.print()

    def quit(self) -> None:
        """Signal the REPL to exit."""
        self._running = False

    def run(self) -> None:
        """Run the interactive console REPL."""
        self._print_banner()

        # Set up prompt session with history and completion
        history = FileHistory(str(self.paths.console_history))
        completer = ConsoleCompleter(self.registry, app=self)

        session: PromptSession = PromptSession(
            history=history,
            completer=completer,
            complete_while_typing=False,
        )

        while self._running:
            try:
                text = session.prompt("wingman> ")
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

            text = text.strip()
            if not text:
                continue

            # Parse and dispatch
            cmd = parse_input(text)
            if cmd is None:
                console.print("[dim]Type a /command. Use /help for a list.[/dim]")
                continue

            # Handle /exit as alias for /quit
            if cmd.command == "exit":
                self.quit()
                continue

            found = self.registry.dispatch(cmd)
            if not found:
                console.print(f"[red]Unknown command: /{cmd.command}[/red]")
                console.print("[dim]Type /help for available commands.[/dim]")

        console.print("[dim]Goodbye.[/dim]")
