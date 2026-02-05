"""Policy management commands."""

from rich.console import Console
from rich.table import Table

from wingman.config.registry import (
    ContactProfile,
    ContactRole,
    ContactTone,
    GroupCategory,
    GroupConfig,
    ReplyPolicy,
)
from wingman.config.yaml_writer import read_yaml, write_yaml

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import print_error, print_success

console = Console()


class PoliciesCommand(BaseCommand):
    name = "policies"
    description = "Manage response policies"
    category = "Policy Management"
    subcommands = {
        "list": "List rules in evaluation order",
        "add": "Add a rule (--condition k=v --action X)",
        "remove": "Remove a rule by name",
        "move": "Reorder a rule (e.g., /policies move rule_name 0)",
        "test": "Simulate policy evaluation for a JID",
        "fallback": "View or set fallback action",
    }

    def execute(self, cmd: ParsedCommand) -> None:
        if cmd.subcommand == "list":
            self._list()
        elif cmd.subcommand == "add":
            self._add(cmd)
        elif cmd.subcommand == "remove":
            self._remove(cmd)
        elif cmd.subcommand == "move":
            self._move(cmd)
        elif cmd.subcommand == "test":
            self._test(cmd)
        elif cmd.subcommand == "fallback":
            self._fallback(cmd)
        else:
            self._list()

    def _get_policies_data(self) -> dict:
        return read_yaml(self.app.paths.policies_config)

    def _save_policies_data(self, data: dict) -> None:
        write_yaml(self.app.paths.policies_config, data)

    def _list(self) -> None:
        data = self._get_policies_data()
        rules = data.get("rules", [])
        if not isinstance(rules, list):
            rules = []
        fallback = data.get("fallback", {})

        if not rules and not fallback:
            console.print("[dim]No policies configured.[/dim]")
            return

        table = Table(title="Policy Rules (evaluation order)")
        table.add_column("#", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Conditions", style="cyan")
        table.add_column("Action", style="magenta")

        for i, rule in enumerate(rules):
            if not isinstance(rule, dict):
                continue
            conditions = rule.get("conditions", {})
            if isinstance(conditions, dict):
                cond_str = ", ".join(f"{k}={v}" for k, v in conditions.items())
            else:
                cond_str = str(conditions)
            table.add_row(str(i), rule.get("name", "unnamed"), cond_str, rule.get("action", "?"))

        console.print(table)

        if isinstance(fallback, dict) and fallback:
            console.print(f"\n  [bold]Fallback:[/bold] {fallback.get('action', 'selective')}")
        console.print()

    def _add(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /policies add <name> --condition k=v --action X")
            return

        name = cmd.args[0]
        action = cmd.flags.get("action", "selective")
        if isinstance(action, bool):
            action = "selective"

        valid_actions = [p.value for p in ReplyPolicy]
        if action not in valid_actions:
            print_error(f"Invalid action: {action}. Choose from: {', '.join(valid_actions)}")
            return

        # Parse conditions from --condition flags
        conditions = {}
        cond_str = cmd.flags.get("condition", "")
        if cond_str and isinstance(cond_str, str):
            for part in cond_str.split(","):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    if v.lower() in ("true", "yes"):
                        conditions[k.strip()] = True
                    elif v.lower() in ("false", "no"):
                        conditions[k.strip()] = False
                    else:
                        conditions[k.strip()] = v.strip()

        data = self._get_policies_data()
        if "rules" not in data or not isinstance(data["rules"], list):
            data["rules"] = []

        data["rules"].append(
            {
                "name": name,
                "conditions": conditions,
                "action": action,
            }
        )

        self._save_policies_data(data)
        print_success(f"Added rule: {name} (action={action})")

    def _remove(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /policies remove <name>")
            return

        name = cmd.args[0]
        data = self._get_policies_data()
        rules = data.get("rules", [])
        if not isinstance(rules, list):
            print_error("Policies config is malformed.")
            return

        original_len = len(rules)
        data["rules"] = [r for r in rules if isinstance(r, dict) and r.get("name") != name]

        if len(data["rules"]) == original_len:
            print_error(f"Rule not found: {name}")
            return

        self._save_policies_data(data)
        print_success(f"Removed rule: {name}")

    def _move(self, cmd: ParsedCommand) -> None:
        if len(cmd.args) < 2:
            print_error("Usage: /policies move <name> <position>")
            return

        name = cmd.args[0]
        try:
            position = int(cmd.args[1])
        except ValueError:
            print_error("Position must be a number.")
            return

        data = self._get_policies_data()
        rules = data.get("rules", [])
        if not isinstance(rules, list):
            print_error("Policies config is malformed.")
            return

        # Find and remove the rule
        rule = None
        for i, r in enumerate(rules):
            if isinstance(r, dict) and r.get("name") == name:
                rule = rules.pop(i)
                break

        if rule is None:
            print_error(f"Rule not found: {name}")
            return

        position = max(0, min(position, len(rules)))
        rules.insert(position, rule)

        self._save_policies_data(data)
        print_success(f"Moved rule '{name}' to position {position}")

    def _test(self, cmd: ParsedCommand) -> None:
        if not cmd.args:
            print_error("Usage: /policies test <jid> [--text 'message text']")
            return

        jid = cmd.args[0]
        text = cmd.flags.get("text", "Hello")
        if isinstance(text, bool):
            text = "Hello"
        is_group = "@g.us" in jid

        bot_name = "Maximus"
        if self.app.settings:
            bot_name = self.app.settings.bot_name

        try:
            from wingman.core.policy import PolicyEvaluator

            evaluator = PolicyEvaluator(self.app.paths.policies_config, bot_name=bot_name)
        except Exception as e:
            print_error(f"Failed to load policy evaluator: {e}")
            return

        # Resolve contact safely
        contacts_data = read_yaml(self.app.paths.contacts_config)
        contacts = contacts_data.get("contacts", {})
        contact_data = contacts.get(jid, {}) if isinstance(contacts, dict) else {}
        if not isinstance(contact_data, dict):
            contact_data = {}

        try:
            contact = ContactProfile(
                jid=jid,
                name=contact_data.get("name", "Unknown"),
                role=ContactRole(contact_data.get("role", "unknown")),
                tone=ContactTone(contact_data.get("tone", "neutral")),
            )
        except ValueError:
            contact = ContactProfile(
                jid=jid, name="Unknown", role=ContactRole.UNKNOWN, tone=ContactTone.NEUTRAL
            )

        # Resolve group safely
        group = None
        if is_group:
            groups_data = read_yaml(self.app.paths.groups_config)
            groups = groups_data.get("groups", {})
            group_data = groups.get(jid, {}) if isinstance(groups, dict) else {}
            if not isinstance(group_data, dict):
                group_data = {}
            try:
                group = GroupConfig(
                    jid=jid,
                    name=group_data.get("name", "Unknown Group"),
                    category=GroupCategory(group_data.get("category", "unknown")),
                    reply_policy=ReplyPolicy(group_data.get("reply_policy", "selective")),
                )
            except ValueError:
                group = GroupConfig(
                    jid=jid,
                    name="Unknown Group",
                    category=GroupCategory.UNKNOWN,
                    reply_policy=ReplyPolicy.SELECTIVE,
                )

        context = evaluator.create_context(
            chat_id=jid,
            sender_id=jid,
            text=text,
            is_group=is_group,
            contact=contact,
            group=group,
        )

        decision = evaluator.evaluate(context)

        console.print("\n  [bold]Policy Test Result[/bold]\n")
        console.print(f"  JID:           {jid}")
        console.print(f"  Contact:       {contact.name} (role={contact.role.value})")
        if group:
            console.print(f"  Group:         {group.name} (category={group.category.value})")
        console.print(f'  Text:          "{text}"')
        console.print(f"  Is mentioned:  {context.is_mentioned}")
        console.print()

        if decision.should_respond:
            console.print(f"  [green]Would respond[/green] (reason: {decision.reason})")
        else:
            console.print(f"  [red]Would NOT respond[/red] (reason: {decision.reason})")

        if decision.rule_name:
            console.print(f"  Matched rule:  {decision.rule_name}")
        console.print(f"  Action:        {decision.action.value}")
        console.print()

    def _fallback(self, cmd: ParsedCommand) -> None:
        data = self._get_policies_data()

        if cmd.args:
            action = cmd.args[0]
            valid = [p.value for p in ReplyPolicy]
            if action not in valid:
                print_error(f"Invalid action: {action}. Choose from: {', '.join(valid)}")
                return
            data["fallback"] = {"action": action}
            self._save_policies_data(data)
            print_success(f"Fallback set to: {action}")
        else:
            fallback = data.get("fallback", {})
            if not isinstance(fallback, dict):
                fallback = {}
            action = fallback.get("action", "selective")
            console.print(f"\n  [bold]Fallback action:[/bold] {action}\n")
