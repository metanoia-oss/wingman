"""Contact management commands."""

import questionary
import yaml
from rich.console import Console
from rich.table import Table

from wingman.config.registry import ContactRole, ContactTone
from wingman.config.yaml_writer import read_yaml, write_yaml

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import print_error, print_success, print_yaml

console = Console()


class ContactsCommand(BaseCommand):
    name = "contacts"
    description = "Manage contacts"
    category = "Contact Management"
    subcommands = {
        "list": "List all contacts (--role to filter)",
        "add": "Add a contact (interactive if no args)",
        "edit": "Edit a contact (--role, --tone, --name)",
        "remove": "Remove a contact",
        "show": "Show a contact's details",
    }

    def execute(self, cmd: ParsedCommand) -> None:
        if cmd.subcommand == "list":
            self._list(cmd)
        elif cmd.subcommand == "add":
            self._add(cmd)
        elif cmd.subcommand == "edit":
            self._edit(cmd)
        elif cmd.subcommand == "remove":
            self._remove(cmd)
        elif cmd.subcommand == "show":
            self._show(cmd)
        else:
            self._list(cmd)

    def _get_contacts_data(self) -> dict:
        return read_yaml(self.app.paths.contacts_config)

    def _save_contacts_data(self, data: dict) -> None:
        write_yaml(self.app.paths.contacts_config, data)

    def _resolve_identifier(self, identifier: str, contacts: dict) -> str | None:
        """Resolve a name or JID to a JID."""
        if identifier in contacts:
            return identifier
        # Search by name (case-insensitive)
        for jid, info in contacts.items():
            if isinstance(info, dict) and info.get("name", "").lower() == identifier.lower():
                return jid
        return None

    def _list(self, cmd: ParsedCommand) -> None:
        data = self._get_contacts_data()
        contacts = data.get("contacts", {})
        if not isinstance(contacts, dict):
            contacts = {}

        if not contacts:
            console.print("[dim]No contacts configured.[/dim]")
            console.print("[dim]Use /contacts add to add one.[/dim]")
            return

        role_filter = cmd.flags.get("role")

        table = Table(title="Contacts")
        table.add_column("Name", style="bold")
        table.add_column("JID", style="dim")
        table.add_column("Role", style="cyan")
        table.add_column("Tone", style="magenta")
        table.add_column("Cooldown")

        for jid, info in contacts.items():
            if not isinstance(info, dict):
                continue
            role = info.get("role", "unknown")
            if role_filter and role != role_filter:
                continue
            table.add_row(
                info.get("name", "Unknown"),
                str(jid),
                str(role),
                str(info.get("tone", "neutral")),
                str(info.get("cooldown_override", "-")),
            )

        console.print(table)

    def _add(self, cmd: ParsedCommand) -> None:
        if cmd.args:
            jid = cmd.args[0]
            name = cmd.flags.get("name", jid)
            role = cmd.flags.get("role", "unknown")
            tone = cmd.flags.get("tone", "neutral")

            # Validate enum values
            valid_roles = [r.value for r in ContactRole]
            valid_tones = [t.value for t in ContactTone]
            if role not in valid_roles:
                print_error(f"Invalid role: {role}. Choose from: {', '.join(valid_roles)}")
                return
            if tone not in valid_tones:
                print_error(f"Invalid tone: {tone}. Choose from: {', '.join(valid_tones)}")
                return
        else:
            # Interactive mode
            try:
                jid = questionary.text("JID (e.g., +1234567890@s.whatsapp.net):").ask()
                if not jid:
                    return
                name = questionary.text("Display name:", default="").ask()
                if not name:
                    name = jid
                role = questionary.select("Role:", choices=[r.value for r in ContactRole]).ask()
                if not role:
                    return
                tone = questionary.select("Tone:", choices=[t.value for t in ContactTone]).ask()
                if not tone:
                    return
            except KeyboardInterrupt:
                console.print("[dim]Cancelled.[/dim]")
                return

        data = self._get_contacts_data()
        if "contacts" not in data or not isinstance(data["contacts"], dict):
            data["contacts"] = {}

        data["contacts"][jid] = {
            "name": str(name),
            "role": str(role),
            "tone": str(tone),
        }

        self._save_contacts_data(data)
        print_success(f"Added contact: {name} ({jid})")

    def _edit(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /contacts edit <jid|name> [--role X] [--tone Y] [--name Z]")
            return

        identifier = cmd.args[0]
        data = self._get_contacts_data()
        contacts = data.get("contacts", {})
        if not isinstance(contacts, dict):
            print_error("Contacts config is malformed.")
            return

        jid = self._resolve_identifier(identifier, contacts)
        if not jid:
            print_error(f"Contact not found: {identifier}")
            return

        contact = contacts[jid]
        if not isinstance(contact, dict):
            print_error(f"Contact entry for {jid} is malformed.")
            return

        if "role" in cmd.flags:
            valid_roles = [r.value for r in ContactRole]
            if cmd.flags["role"] not in valid_roles:
                print_error(f"Invalid role. Choose from: {', '.join(valid_roles)}")
                return
            contact["role"] = cmd.flags["role"]
        if "tone" in cmd.flags:
            valid_tones = [t.value for t in ContactTone]
            if cmd.flags["tone"] not in valid_tones:
                print_error(f"Invalid tone. Choose from: {', '.join(valid_tones)}")
                return
            contact["tone"] = cmd.flags["tone"]
        if "name" in cmd.flags:
            contact["name"] = cmd.flags["name"]
        if "cooldown_override" in cmd.flags:
            try:
                contact["cooldown_override"] = int(cmd.flags["cooldown_override"])
            except (ValueError, TypeError):
                print_error("cooldown_override must be a number (seconds).")
                return

        self._save_contacts_data(data)
        print_success(f"Updated contact: {contact.get('name', jid)}")

    def _remove(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /contacts remove <jid|name>")
            return

        identifier = cmd.args[0]
        data = self._get_contacts_data()
        contacts = data.get("contacts", {})
        if not isinstance(contacts, dict):
            print_error("Contacts config is malformed.")
            return

        jid = self._resolve_identifier(identifier, contacts)
        if not jid:
            print_error(f"Contact not found: {identifier}")
            return

        name = contacts[jid].get("name", jid) if isinstance(contacts[jid], dict) else jid
        del contacts[jid]
        self._save_contacts_data(data)
        print_success(f"Removed contact: {name}")

    def _show(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /contacts show <jid|name>")
            return

        identifier = cmd.args[0]
        data = self._get_contacts_data()
        contacts = data.get("contacts", {})
        if not isinstance(contacts, dict):
            print_error("Contacts config is malformed.")
            return

        jid = self._resolve_identifier(identifier, contacts)
        if not jid:
            print_error(f"Contact not found: {identifier}")
            return

        contact = contacts[jid]
        content = yaml.dump({jid: contact}, default_flow_style=False)
        title = contact.get("name", jid) if isinstance(contact, dict) else jid
        print_yaml(content, title=title)
