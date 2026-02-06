"""Send message command."""

from rich.console import Console

from wingman.config.yaml_writer import read_yaml
from wingman.core.rpc_client import RPCError

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import print_error, print_success

console = Console()


class SendCommand(BaseCommand):
    name = "send"
    description = "Send a message via the bot"
    category = "Messaging"
    usage = "/send <name|jid> <message>"
    examples = [
        "/send John Hello, how are you?",
        "/send +1234567890@s.whatsapp.net Hey there!",
    ]

    def execute(self, cmd: ParsedCommand) -> None:
        if not cmd.subcommand:
            print_error("Usage: /send <name|jid> <message>")
            return

        recipient = cmd.subcommand
        message_parts = cmd.args
        if not message_parts:
            print_error("Usage: /send <name|jid> <message>")
            return

        message = " ".join(message_parts)
        jid = self._resolve_recipient(recipient)

        if not jid:
            print_error(f"Could not resolve recipient: {recipient}")
            return

        # Determine platform from JID
        platform = "whatsapp"
        if jid.startswith("imessage:"):
            platform = "imessage"

        try:
            result = self.app.rpc.send_message(jid, message, platform)
            if result.get("success"):
                print_success(f"Message sent to {recipient}.")
            else:
                print_error(f"Failed to send: {result.get('error', 'unknown error')}")
        except RPCError as e:
            print_error(f"Failed to send: {e}")

    def _resolve_recipient(self, identifier: str) -> str | None:
        """Resolve a name or JID to a JID."""
        # If it looks like a JID already, use it directly
        if "@" in identifier:
            return identifier

        # Search contacts by name
        contacts_data = read_yaml(self.app.paths.contacts_config)
        contacts = contacts_data.get("contacts", {})
        for jid, info in contacts.items():
            if info.get("name", "").lower() == identifier.lower():
                return jid

        return None
