"""Group management commands."""

import questionary
import yaml
from rich.console import Console
from rich.table import Table

from wingman.config.registry import GroupCategory, ReplyPolicy
from wingman.config.yaml_writer import read_yaml, write_yaml

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import print_error, print_success, print_yaml

console = Console()


class GroupsCommand(BaseCommand):
    name = "groups"
    description = "Manage groups"
    category = "Group Management"
    subcommands = {
        "list": "List all groups",
        "add": "Add a group (interactive if no args)",
        "edit": "Edit a group (--category, --policy, --name)",
        "remove": "Remove a group",
    }

    def execute(self, cmd: ParsedCommand) -> None:
        if cmd.subcommand == "list":
            self._list()
        elif cmd.subcommand == "add":
            self._add(cmd)
        elif cmd.subcommand == "edit":
            self._edit(cmd)
        elif cmd.subcommand == "remove":
            self._remove(cmd)
        else:
            self._list()

    def _get_groups_data(self) -> dict:
        return read_yaml(self.app.paths.groups_config)

    def _save_groups_data(self, data: dict) -> None:
        write_yaml(self.app.paths.groups_config, data)

    def _resolve_identifier(self, identifier: str, groups: dict) -> str | None:
        """Resolve a name or JID to a JID."""
        if identifier in groups:
            return identifier
        for jid, info in groups.items():
            if isinstance(info, dict) and info.get("name", "").lower() == identifier.lower():
                return jid
        return None

    def _list(self) -> None:
        data = self._get_groups_data()
        groups = data.get("groups", {})
        if not isinstance(groups, dict):
            groups = {}

        if not groups:
            console.print("[dim]No groups configured.[/dim]")
            console.print("[dim]Use /groups add to add one.[/dim]")
            return

        table = Table(title="Groups")
        table.add_column("Name", style="bold")
        table.add_column("JID", style="dim")
        table.add_column("Category", style="cyan")
        table.add_column("Reply Policy", style="magenta")

        for jid, info in groups.items():
            if not isinstance(info, dict):
                continue
            table.add_row(
                info.get("name", "Unknown Group"),
                str(jid),
                str(info.get("category", "unknown")),
                str(info.get("reply_policy", "selective")),
            )

        console.print(table)

    def _add(self, cmd: ParsedCommand) -> None:
        if cmd.args:
            jid = cmd.args[0]
            name = cmd.flags.get("name", jid)
            category = cmd.flags.get("category", "unknown")
            policy = cmd.flags.get("policy", "selective")

            valid_categories = [c.value for c in GroupCategory]
            valid_policies = [p.value for p in ReplyPolicy]
            if category not in valid_categories:
                print_error(f"Invalid category: {category}. Choose from: {', '.join(valid_categories)}")
                return
            if policy not in valid_policies:
                print_error(f"Invalid policy: {policy}. Choose from: {', '.join(valid_policies)}")
                return
        else:
            try:
                jid = questionary.text(
                    "Group JID (e.g., 120363012345678901@g.us):"
                ).ask()
                if not jid:
                    return
                name = questionary.text("Display name:", default="").ask()
                if not name:
                    name = jid
                category = questionary.select(
                    "Category:", choices=[c.value for c in GroupCategory]
                ).ask()
                if not category:
                    return
                policy = questionary.select(
                    "Reply policy:", choices=[p.value for p in ReplyPolicy]
                ).ask()
                if not policy:
                    return
            except KeyboardInterrupt:
                console.print("[dim]Cancelled.[/dim]")
                return

        data = self._get_groups_data()
        if "groups" not in data or not isinstance(data["groups"], dict):
            data["groups"] = {}

        data["groups"][jid] = {
            "name": str(name),
            "category": str(category),
            "reply_policy": str(policy),
        }

        self._save_groups_data(data)
        print_success(f"Added group: {name} ({jid})")

    def _edit(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /groups edit <jid|name> [--category X] [--policy Y] [--name Z]")
            return

        identifier = cmd.args[0]
        data = self._get_groups_data()
        groups = data.get("groups", {})
        if not isinstance(groups, dict):
            print_error("Groups config is malformed.")
            return

        jid = self._resolve_identifier(identifier, groups)
        if not jid:
            print_error(f"Group not found: {identifier}")
            return

        group = groups[jid]
        if not isinstance(group, dict):
            print_error(f"Group entry for {jid} is malformed.")
            return

        if "category" in cmd.flags:
            valid = [c.value for c in GroupCategory]
            if cmd.flags["category"] not in valid:
                print_error(f"Invalid category. Choose from: {', '.join(valid)}")
                return
            group["category"] = cmd.flags["category"]
        if "policy" in cmd.flags:
            valid = [p.value for p in ReplyPolicy]
            if cmd.flags["policy"] not in valid:
                print_error(f"Invalid policy. Choose from: {', '.join(valid)}")
                return
            group["reply_policy"] = cmd.flags["policy"]
        if "name" in cmd.flags:
            group["name"] = cmd.flags["name"]

        self._save_groups_data(data)
        print_success(f"Updated group: {group.get('name', jid)}")

    def _remove(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /groups remove <jid|name>")
            return

        identifier = cmd.args[0]
        data = self._get_groups_data()
        groups = data.get("groups", {})
        if not isinstance(groups, dict):
            print_error("Groups config is malformed.")
            return

        jid = self._resolve_identifier(identifier, groups)
        if not jid:
            print_error(f"Group not found: {identifier}")
            return

        name = groups[jid].get("name", jid) if isinstance(groups[jid], dict) else jid
        del groups[jid]
        self._save_groups_data(data)
        print_success(f"Removed group: {name}")
