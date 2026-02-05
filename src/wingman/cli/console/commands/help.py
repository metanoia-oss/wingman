"""Help and quit commands."""

from collections import defaultdict

from rich.console import Console
from rich.table import Table

from wingman import __version__

from ..command_registry import BaseCommand
from ..parser import ParsedCommand

console = Console()


class HelpCommand(BaseCommand):
    name = "help"
    description = "Show all commands or help for one"
    category = "Help & Navigation"

    def execute(self, cmd: ParsedCommand) -> None:
        if cmd.subcommand:
            self._show_command_help(cmd.subcommand)
        else:
            self._show_all()

    def _show_command_help(self, name: str) -> None:
        command = self.app.registry.get(name)
        if not command:
            console.print(f"[red]Unknown command: /{name}[/red]")
            return

        console.print(f"\n  [bold]/{command.name}[/bold] - {command.description}\n")

        if command.subcommands:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column("Subcommand", style="bold cyan")
            table.add_column("Description")
            for sub, desc in command.subcommands.items():
                table.add_row(f"/{command.name} {sub}", desc)
            console.print(table)
            console.print()

    def _show_all(self) -> None:
        commands = self.app.registry.all_commands()

        # Group by category
        categories: dict[str, list] = defaultdict(list)
        for cmd in commands.values():
            categories[cmd.category].append(cmd)

        console.print(f"\n  [bold blue]Wingman Console[/bold blue] v{__version__}\n")

        category_order = [
            "Help & Navigation",
            "Bot Control",
            "Configuration",
            "Contact Management",
            "Group Management",
            "Policy Management",
            "Messaging",
            "Stats",
        ]

        for cat in category_order:
            cmds = categories.get(cat, [])
            if not cmds:
                continue
            console.print(f"  [bold]{cat}[/bold]")
            for c in cmds:
                name_col = f"/{c.name}"
                console.print(f"    {name_col:<20} {c.description}")
            console.print()


class QuitCommand(BaseCommand):
    name = "quit"
    description = "Exit the console"
    category = "Help & Navigation"

    def execute(self, cmd: ParsedCommand) -> None:
        self.app.quit()
