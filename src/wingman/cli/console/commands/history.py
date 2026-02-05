"""Chat history commands."""

from datetime import datetime

from rich.console import Console
from rich.table import Table

from wingman.config.yaml_writer import read_yaml
from wingman.core.memory.models import MessageStore

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import print_error

console = Console()


class ChatsCommand(BaseCommand):
    name = "chats"
    description = "List recent chats"
    category = "Messaging"

    def execute(self, cmd: ParsedCommand) -> None:
        limit = 20
        if "n" in cmd.flags:
            try:
                limit = int(cmd.flags["n"])
            except (ValueError, TypeError):
                pass

        db_path = self.app.paths.db_path
        if not db_path.exists():
            console.print("[dim]No message history found.[/dim]")
            return

        store = MessageStore(db_path)
        chats = store.get_recent_chats(limit)

        if not chats:
            console.print("[dim]No chats found.[/dim]")
            return

        # Build contact name lookup
        contacts_data = read_yaml(self.app.paths.contacts_config)
        contacts = contacts_data.get("contacts", {})
        name_map = {jid: info.get("name", jid) for jid, info in contacts.items()}

        table = Table(title="Recent Chats")
        table.add_column("Chat", style="bold")
        table.add_column("Last Message", style="dim", max_width=50)
        table.add_column("Time", style="cyan")
        table.add_column("Platform")

        for chat in chats:
            chat_id = chat["chat_id"]
            display_name = name_map.get(chat_id, chat_id[:25])
            ts = datetime.fromtimestamp(chat["timestamp"]).strftime("%Y-%m-%d %H:%M")
            table.add_row(display_name, chat["last_message"][:50], ts, chat["platform"])

        console.print(table)


class HistoryCommand(BaseCommand):
    name = "history"
    description = "View chat history"
    category = "Messaging"

    def execute(self, cmd: ParsedCommand) -> None:
        if not cmd.subcommand:
            print_error("Usage: /history <name|jid> [-n 30]")
            return

        identifier = cmd.subcommand
        limit = 30
        if "n" in cmd.flags:
            try:
                limit = int(cmd.flags["n"])
            except (ValueError, TypeError):
                pass

        db_path = self.app.paths.db_path
        if not db_path.exists():
            console.print("[dim]No message history found.[/dim]")
            return

        # Resolve identifier to chat_id
        chat_id = self._resolve_chat(identifier)
        if not chat_id:
            print_error(f"Could not resolve: {identifier}")
            return

        store = MessageStore(db_path)
        messages = store.get_recent_messages(chat_id, limit)

        if not messages:
            console.print("[dim]No messages found for this chat.[/dim]")
            return

        bot_name = "Bot"
        if self.app.settings:
            bot_name = self.app.settings.bot_name

        console.print(f"\n  [bold]Chat history: {identifier}[/bold] (last {len(messages)})\n")

        for msg in messages:
            ts = datetime.fromtimestamp(msg.timestamp).strftime("%H:%M")
            if msg.is_self:
                console.print(f"  [dim]{ts}[/dim] [bold blue]{bot_name}:[/bold blue] {msg.text}")
            else:
                name = msg.sender_name or msg.sender_id[:15]
                console.print(f"  [dim]{ts}[/dim] [bold]{name}:[/bold] {msg.text}")

        console.print()

    def _resolve_chat(self, identifier: str) -> str | None:
        """Resolve a name or JID to a chat_id."""
        if "@" in identifier:
            return identifier

        # Search contacts
        contacts_data = read_yaml(self.app.paths.contacts_config)
        contacts = contacts_data.get("contacts", {})
        for jid, info in contacts.items():
            if info.get("name", "").lower() == identifier.lower():
                return jid

        # Search groups
        groups_data = read_yaml(self.app.paths.groups_config)
        groups = groups_data.get("groups", {})
        for jid, info in groups.items():
            if info.get("name", "").lower() == identifier.lower():
                return jid

        return None
