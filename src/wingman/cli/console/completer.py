"""Tab completion for the interactive console."""

from __future__ import annotations

from typing import TYPE_CHECKING

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

if TYPE_CHECKING:
    from .app import ConsoleApp
    from .command_registry import CommandRegistry

# Commands that accept contact/group names as their subcommand argument
_CONTACT_COMMANDS = {"send", "history"}
_CONTACT_SUBCOMMANDS = {"contacts": {"edit", "remove", "show"}}
_GROUP_SUBCOMMANDS = {"groups": {"edit", "remove"}}

# Flag value completions
_FLAG_VALUES = {
    "role": ["girlfriend", "sister", "friend", "family", "colleague", "unknown"],
    "tone": ["affectionate", "loving", "friendly", "casual", "sarcastic", "neutral"],
    "category": ["family", "friends", "work", "unknown"],
    "policy": ["always", "selective", "never"],
    "action": ["always", "selective", "never"],
}


class ConsoleCompleter(Completer):
    """Tab-completion provider for the console REPL."""

    def __init__(self, registry: CommandRegistry, app: ConsoleApp | None = None) -> None:
        self._registry = registry
        self._app = app

    def _get_contact_names(self) -> list[str]:
        """Get all contact names for completion."""
        if not self._app:
            return []
        try:
            from wingman.config.yaml_writer import read_yaml

            data = read_yaml(self._app.paths.contacts_config)
            contacts = data.get("contacts", {})
            return [info.get("name", jid) for jid, info in contacts.items() if info.get("name")]
        except Exception:
            return []

    def _get_group_names(self) -> list[str]:
        """Get all group names for completion."""
        if not self._app:
            return []
        try:
            from wingman.config.yaml_writer import read_yaml

            data = read_yaml(self._app.paths.groups_config)
            groups = data.get("groups", {})
            return [info.get("name", jid) for jid, info in groups.items() if info.get("name")]
        except Exception:
            return []

    def get_completions(self, document: Document, complete_event: CompleteEvent):
        text = document.text_before_cursor.lstrip()

        if not text:
            for name in sorted(self._registry.all_commands()):
                yield Completion(f"/{name}", start_position=0, display_meta="command")
            return

        if not text.startswith("/"):
            return

        parts = text.split()

        if len(parts) <= 1:
            # Completing the command name
            prefix = text[1:]
            for name in sorted(self._registry.all_commands()):
                if name.startswith(prefix):
                    cmd = self._registry.get(name)
                    meta = cmd.description[:40] if cmd else ""
                    yield Completion(f"/{name}", start_position=-len(text), display_meta=meta)
            return

        cmd_name = parts[0][1:]

        if len(parts) == 2 and not text.endswith(" "):
            # Typing subcommand
            sub_prefix = parts[1].lower()

            # Offer subcommands
            for sub in self._registry.get_subcommand_completions(cmd_name):
                if sub.startswith(sub_prefix):
                    yield Completion(sub, start_position=-len(sub_prefix))

            # Offer contact names for commands like /send, /history
            if cmd_name in _CONTACT_COMMANDS:
                for name in self._get_contact_names():
                    if name.lower().startswith(sub_prefix):
                        yield Completion(
                            name, start_position=-len(sub_prefix), display_meta="contact"
                        )
            return

        if len(parts) == 2 and text.endswith(" "):
            # Just typed subcommand, show further completions
            sub = parts[1].lower()

            # Show subcommands if not typed yet
            subs = self._registry.get_subcommand_completions(cmd_name)
            if sub not in subs:
                for s in subs:
                    yield Completion(s, start_position=0)
                return

            # After subcommand, offer contact/group names
            if cmd_name in _CONTACT_SUBCOMMANDS and sub in _CONTACT_SUBCOMMANDS[cmd_name]:
                for name in self._get_contact_names():
                    yield Completion(name, start_position=0, display_meta="contact")
            elif cmd_name in _GROUP_SUBCOMMANDS and sub in _GROUP_SUBCOMMANDS[cmd_name]:
                for name in self._get_group_names():
                    yield Completion(name, start_position=0, display_meta="group")
            return

        # Flag value completion
        if len(parts) >= 3:
            prev = parts[-2] if not text.endswith(" ") else parts[-1]
            current = parts[-1] if not text.endswith(" ") else ""

            # Check if previous token is a flag that has known values
            flag_name = prev.lstrip("-")
            if flag_name in _FLAG_VALUES:
                prefix = current.lower()
                for val in _FLAG_VALUES[flag_name]:
                    if val.startswith(prefix):
                        yield Completion(
                            val,
                            start_position=-len(current) if current else 0,
                            display_meta=flag_name,
                        )
                return

            # Config section completion: /config show <section>
            if (
                text.endswith(" ")
                and cmd_name == "config"
                and len(parts) == 2
                and parts[1] == "show"
            ):
                for section in ["openai", "safety", "bot", "imessage"]:
                    yield Completion(section, start_position=0, display_meta="section")
                return

            if (
                len(parts) == 3
                and not text.endswith(" ")
                and cmd_name == "config"
                and parts[1] == "show"
            ):
                prefix = parts[2].lower()
                for section in ["openai", "safety", "bot", "imessage"]:
                    if section.startswith(prefix):
                        yield Completion(
                            section, start_position=-len(prefix), display_meta="section"
                        )
                return

            # If text ends with space and last word is a name/subcommand,
            # offer common flags
            if text.endswith(" ") and cmd_name == "contacts" and parts[1] in ("edit", "add"):
                for flag in ["--role", "--tone", "--name", "--cooldown_override"]:
                    yield Completion(flag, start_position=0)
            elif text.endswith(" ") and cmd_name == "groups" and parts[1] in ("edit", "add"):
                for flag in ["--category", "--policy", "--name"]:
                    yield Completion(flag, start_position=0)
