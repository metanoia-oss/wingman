"""Stats and activity commands."""

from datetime import datetime

from rich.console import Console
from rich.table import Table

from wingman.core.memory.models import MessageStore
from wingman.core.rpc_client import RPCError

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import format_uptime

console = Console()


class StatsCommand(BaseCommand):
    name = "stats"
    description = "Overall bot statistics"
    category = "Stats"

    def execute(self, cmd: ParsedCommand) -> None:
        db_path = self.app.paths.db_path
        if not db_path.exists():
            console.print("[dim]No data yet.[/dim]")
            return

        store = MessageStore(db_path)
        stats = store.get_stats()

        console.print("\n  [bold]Bot Statistics[/bold]\n")
        console.print(f"  Total messages:   {stats['total_messages']}")
        console.print(f"  Sent (by bot):    {stats['sent']}")
        console.print(f"  Received:         {stats['received']}")
        console.print(f"  Active chats:     {stats['active_chats']}")
        console.print(f"  Last 24h:         {stats['messages_last_24h']}")

        # Add daemon uptime if running
        try:
            status = self.app.rpc.get_status()
            uptime = status.get("uptime")
            if uptime:
                console.print(f"  Daemon uptime:    {format_uptime(uptime)}")
        except RPCError:
            pass

        console.print()


class ActivityCommand(BaseCommand):
    name = "activity"
    description = "Recent bot activity"
    category = "Stats"

    def execute(self, cmd: ParsedCommand) -> None:
        limit = 20
        if "n" in cmd.flags:
            try:
                limit = int(cmd.flags["n"])
            except (ValueError, TypeError):
                pass

        db_path = self.app.paths.db_path
        if not db_path.exists():
            console.print("[dim]No activity yet.[/dim]")
            return

        store = MessageStore(db_path)
        activity = store.get_recent_activity(limit)

        if not activity:
            console.print("[dim]No bot activity found.[/dim]")
            return

        table = Table(title="Recent Bot Activity")
        table.add_column("Time", style="cyan")
        table.add_column("Chat", style="dim")
        table.add_column("Message", max_width=60)
        table.add_column("Platform")

        for entry in activity:
            ts = datetime.fromtimestamp(entry["timestamp"]).strftime("%Y-%m-%d %H:%M")
            table.add_row(ts, entry["chat_id"][:25], entry["text"][:60], entry["platform"])

        console.print(table)
