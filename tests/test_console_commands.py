"""Tests for console commands (config, contacts, groups, policies)."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import yaml

from wingman.cli.console.command_registry import CommandRegistry
from wingman.cli.console.commands.config import ConfigCommand
from wingman.cli.console.commands.contacts import ContactsCommand
from wingman.cli.console.commands.groups import GroupsCommand
from wingman.cli.console.commands.help import HelpCommand, QuitCommand
from wingman.cli.console.commands.policies import PoliciesCommand
from wingman.cli.console.parser import ParsedCommand, parse_input
from wingman.config.yaml_writer import read_yaml


class FakeApp:
    """Fake ConsoleApp with temp directory for paths."""

    def __init__(self, tmp_path: Path):
        self.paths = MagicMock()
        self.paths.config_file = tmp_path / "config.yaml"
        self.paths.contacts_config = tmp_path / "contacts.yaml"
        self.paths.groups_config = tmp_path / "groups.yaml"
        self.paths.policies_config = tmp_path / "policies.yaml"
        self.paths.config_exists.return_value = True
        self.settings = None
        self.registry = CommandRegistry()
        self._running = True

    def quit(self):
        self._running = False


class TestHelpCommand:
    def test_help_runs(self, tmp_path):
        app = FakeApp(tmp_path)
        # Register some commands so /help has something to show
        app.registry.register(HelpCommand(app))
        app.registry.register(QuitCommand(app))
        cmd = HelpCommand(app)
        cmd.execute(ParsedCommand(command="help"))  # should not raise

    def test_help_specific_command(self, tmp_path):
        app = FakeApp(tmp_path)
        app.registry.register(HelpCommand(app))
        cmd = HelpCommand(app)
        cmd.execute(ParsedCommand(command="help", subcommand="help"))  # should not raise

    def test_help_unknown_command(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = HelpCommand(app)
        cmd.execute(ParsedCommand(command="help", subcommand="nonexistent"))  # should not raise


class TestQuitCommand:
    def test_quit(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = QuitCommand(app)
        assert app._running is True
        cmd.execute(ParsedCommand(command="quit"))
        assert app._running is False


class TestConfigCommand:
    def test_show_no_config(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = ConfigCommand(app)
        # File doesn't exist, should handle gracefully
        cmd.execute(ParsedCommand(command="config", subcommand="show"))

    def test_show_with_config(self, tmp_path):
        app = FakeApp(tmp_path)
        config_data = {"bot": {"name": "TestBot"}, "openai": {"model": "gpt-4o"}}
        app.paths.config_file.write_text(yaml.dump(config_data))
        cmd = ConfigCommand(app)
        cmd.execute(ParsedCommand(command="config", subcommand="show"))

    def test_show_section(self, tmp_path):
        app = FakeApp(tmp_path)
        config_data = {"bot": {"name": "TestBot"}, "openai": {"model": "gpt-4o"}}
        app.paths.config_file.write_text(yaml.dump(config_data))
        cmd = ConfigCommand(app)
        cmd.execute(ParsedCommand(command="config", subcommand="show", args=["bot"]))

    def test_show_invalid_section(self, tmp_path):
        app = FakeApp(tmp_path)
        config_data = {"bot": {"name": "TestBot"}}
        app.paths.config_file.write_text(yaml.dump(config_data))
        cmd = ConfigCommand(app)
        cmd.execute(ParsedCommand(command="config", subcommand="show", args=["nonexistent"]))

    def test_set_value(self, tmp_path):
        app = FakeApp(tmp_path)
        config_data = {"bot": {"name": "TestBot"}}
        app.paths.config_file.write_text(yaml.dump(config_data))
        cmd = ConfigCommand(app)
        cmd.execute(
            ParsedCommand(command="config", subcommand="set", args=["bot.name", "NewBot"])
        )
        result = read_yaml(app.paths.config_file)
        assert result["bot"]["name"] == "NewBot"

    def test_set_nested_value(self, tmp_path):
        app = FakeApp(tmp_path)
        config_data = {"openai": {"model": "gpt-4o"}}
        app.paths.config_file.write_text(yaml.dump(config_data))
        cmd = ConfigCommand(app)
        cmd.execute(
            ParsedCommand(
                command="config", subcommand="set", args=["openai.model", "gpt-4-turbo"]
            )
        )
        result = read_yaml(app.paths.config_file)
        assert result["openai"]["model"] == "gpt-4-turbo"

    def test_set_no_args(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = ConfigCommand(app)
        cmd.execute(ParsedCommand(command="config", subcommand="set"))  # should not raise

    def test_api_key_masked(self, tmp_path):
        app = FakeApp(tmp_path)
        config_data = {"openai": {"api_key": "sk-1234567890abcdef"}}
        app.paths.config_file.write_text(yaml.dump(config_data))
        cmd = ConfigCommand(app)
        # Just verify it doesn't crash when masking
        cmd.execute(ParsedCommand(command="config", subcommand="show"))


class TestContactsCommand:
    def test_list_empty(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = ContactsCommand(app)
        cmd.execute(ParsedCommand(command="contacts", subcommand="list"))

    def test_add_with_args(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = ContactsCommand(app)
        cmd.execute(
            ParsedCommand(
                command="contacts",
                subcommand="add",
                args=["+1234@s.whatsapp.net"],
                flags={"name": "John", "role": "friend", "tone": "casual"},
            )
        )
        data = read_yaml(app.paths.contacts_config)
        assert "+1234@s.whatsapp.net" in data["contacts"]
        assert data["contacts"]["+1234@s.whatsapp.net"]["name"] == "John"

    def test_add_invalid_role(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = ContactsCommand(app)
        cmd.execute(
            ParsedCommand(
                command="contacts",
                subcommand="add",
                args=["+1234@s.whatsapp.net"],
                flags={"role": "invalid_role"},
            )
        )
        data = read_yaml(app.paths.contacts_config)
        assert not data.get("contacts")

    def test_edit_contact(self, tmp_path):
        app = FakeApp(tmp_path)
        # Pre-populate
        contacts_data = {
            "contacts": {"+1234@s.whatsapp.net": {"name": "John", "role": "friend", "tone": "casual"}}
        }
        app.paths.contacts_config.write_text(yaml.dump(contacts_data))

        cmd = ContactsCommand(app)
        cmd.execute(
            ParsedCommand(
                command="contacts", subcommand="edit", args=["John"], flags={"tone": "sarcastic"}
            )
        )
        data = read_yaml(app.paths.contacts_config)
        assert data["contacts"]["+1234@s.whatsapp.net"]["tone"] == "sarcastic"

    def test_edit_invalid_tone(self, tmp_path):
        app = FakeApp(tmp_path)
        contacts_data = {
            "contacts": {"+1234@s.whatsapp.net": {"name": "John", "role": "friend", "tone": "casual"}}
        }
        app.paths.contacts_config.write_text(yaml.dump(contacts_data))

        cmd = ContactsCommand(app)
        cmd.execute(
            ParsedCommand(
                command="contacts", subcommand="edit", args=["John"], flags={"tone": "INVALID"}
            )
        )
        data = read_yaml(app.paths.contacts_config)
        # Should not have changed
        assert data["contacts"]["+1234@s.whatsapp.net"]["tone"] == "casual"

    def test_remove_contact(self, tmp_path):
        app = FakeApp(tmp_path)
        contacts_data = {
            "contacts": {"+1234@s.whatsapp.net": {"name": "John", "role": "friend", "tone": "casual"}}
        }
        app.paths.contacts_config.write_text(yaml.dump(contacts_data))

        cmd = ContactsCommand(app)
        cmd.execute(ParsedCommand(command="contacts", subcommand="remove", args=["John"]))
        data = read_yaml(app.paths.contacts_config)
        assert "+1234@s.whatsapp.net" not in data.get("contacts", {})

    def test_remove_not_found(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = ContactsCommand(app)
        cmd.execute(ParsedCommand(command="contacts", subcommand="remove", args=["Nobody"]))

    def test_show_contact(self, tmp_path):
        app = FakeApp(tmp_path)
        contacts_data = {
            "contacts": {"+1234@s.whatsapp.net": {"name": "John", "role": "friend", "tone": "casual"}}
        }
        app.paths.contacts_config.write_text(yaml.dump(contacts_data))
        cmd = ContactsCommand(app)
        cmd.execute(ParsedCommand(command="contacts", subcommand="show", args=["John"]))

    def test_resolve_by_jid(self, tmp_path):
        app = FakeApp(tmp_path)
        contacts_data = {
            "contacts": {"+1234@s.whatsapp.net": {"name": "John", "role": "friend", "tone": "casual"}}
        }
        app.paths.contacts_config.write_text(yaml.dump(contacts_data))
        cmd = ContactsCommand(app)
        cmd.execute(
            ParsedCommand(command="contacts", subcommand="show", args=["+1234@s.whatsapp.net"])
        )

    def test_malformed_contacts_file(self, tmp_path):
        app = FakeApp(tmp_path)
        app.paths.contacts_config.write_text("contacts: not_a_dict")
        cmd = ContactsCommand(app)
        cmd.execute(ParsedCommand(command="contacts", subcommand="list"))  # should not raise


class TestGroupsCommand:
    def test_list_empty(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = GroupsCommand(app)
        cmd.execute(ParsedCommand(command="groups", subcommand="list"))

    def test_add_group(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = GroupsCommand(app)
        cmd.execute(
            ParsedCommand(
                command="groups",
                subcommand="add",
                args=["123@g.us"],
                flags={"name": "Family", "category": "family", "policy": "always"},
            )
        )
        data = read_yaml(app.paths.groups_config)
        assert "123@g.us" in data["groups"]
        assert data["groups"]["123@g.us"]["name"] == "Family"

    def test_add_invalid_category(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = GroupsCommand(app)
        cmd.execute(
            ParsedCommand(
                command="groups",
                subcommand="add",
                args=["123@g.us"],
                flags={"category": "invalid"},
            )
        )
        data = read_yaml(app.paths.groups_config)
        assert not data.get("groups")

    def test_edit_group(self, tmp_path):
        app = FakeApp(tmp_path)
        groups_data = {
            "groups": {"123@g.us": {"name": "Family", "category": "family", "reply_policy": "always"}}
        }
        app.paths.groups_config.write_text(yaml.dump(groups_data))

        cmd = GroupsCommand(app)
        cmd.execute(
            ParsedCommand(
                command="groups", subcommand="edit", args=["Family"], flags={"policy": "never"}
            )
        )
        data = read_yaml(app.paths.groups_config)
        assert data["groups"]["123@g.us"]["reply_policy"] == "never"

    def test_remove_group(self, tmp_path):
        app = FakeApp(tmp_path)
        groups_data = {
            "groups": {"123@g.us": {"name": "Family", "category": "family", "reply_policy": "always"}}
        }
        app.paths.groups_config.write_text(yaml.dump(groups_data))

        cmd = GroupsCommand(app)
        cmd.execute(ParsedCommand(command="groups", subcommand="remove", args=["Family"]))
        data = read_yaml(app.paths.groups_config)
        assert "123@g.us" not in data.get("groups", {})


class TestPoliciesCommand:
    def test_list_empty(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = PoliciesCommand(app)
        cmd.execute(ParsedCommand(command="policies", subcommand="list"))

    def test_add_rule(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = PoliciesCommand(app)
        cmd.execute(
            ParsedCommand(
                command="policies",
                subcommand="add",
                args=["dm_rule"],
                flags={"condition": "is_dm=true", "action": "always"},
            )
        )
        data = read_yaml(app.paths.policies_config)
        assert len(data["rules"]) == 1
        assert data["rules"][0]["name"] == "dm_rule"
        assert data["rules"][0]["action"] == "always"

    def test_add_invalid_action(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = PoliciesCommand(app)
        cmd.execute(
            ParsedCommand(
                command="policies",
                subcommand="add",
                args=["bad_rule"],
                flags={"action": "invalid_action"},
            )
        )
        data = read_yaml(app.paths.policies_config)
        assert not data.get("rules")

    def test_remove_rule(self, tmp_path):
        app = FakeApp(tmp_path)
        policies_data = {
            "rules": [{"name": "test_rule", "conditions": {}, "action": "always"}]
        }
        app.paths.policies_config.write_text(yaml.dump(policies_data))

        cmd = PoliciesCommand(app)
        cmd.execute(ParsedCommand(command="policies", subcommand="remove", args=["test_rule"]))
        data = read_yaml(app.paths.policies_config)
        assert len(data["rules"]) == 0

    def test_remove_nonexistent(self, tmp_path):
        app = FakeApp(tmp_path)
        policies_data = {
            "rules": [{"name": "test_rule", "conditions": {}, "action": "always"}]
        }
        app.paths.policies_config.write_text(yaml.dump(policies_data))

        cmd = PoliciesCommand(app)
        cmd.execute(ParsedCommand(command="policies", subcommand="remove", args=["nonexistent"]))
        data = read_yaml(app.paths.policies_config)
        assert len(data["rules"]) == 1

    def test_move_rule(self, tmp_path):
        app = FakeApp(tmp_path)
        policies_data = {
            "rules": [
                {"name": "rule_a", "conditions": {}, "action": "always"},
                {"name": "rule_b", "conditions": {}, "action": "never"},
            ]
        }
        app.paths.policies_config.write_text(yaml.dump(policies_data))

        cmd = PoliciesCommand(app)
        cmd.execute(ParsedCommand(command="policies", subcommand="move", args=["rule_b", "0"]))
        data = read_yaml(app.paths.policies_config)
        assert data["rules"][0]["name"] == "rule_b"
        assert data["rules"][1]["name"] == "rule_a"

    def test_fallback_show(self, tmp_path):
        app = FakeApp(tmp_path)
        policies_data = {"fallback": {"action": "never"}}
        app.paths.policies_config.write_text(yaml.dump(policies_data))
        cmd = PoliciesCommand(app)
        cmd.execute(ParsedCommand(command="policies", subcommand="fallback"))

    def test_fallback_set(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = PoliciesCommand(app)
        cmd.execute(
            ParsedCommand(command="policies", subcommand="fallback", args=["never"])
        )
        data = read_yaml(app.paths.policies_config)
        assert data["fallback"]["action"] == "never"

    def test_fallback_invalid(self, tmp_path):
        app = FakeApp(tmp_path)
        cmd = PoliciesCommand(app)
        cmd.execute(
            ParsedCommand(command="policies", subcommand="fallback", args=["invalid"])
        )

    def test_policy_test(self, tmp_path):
        app = FakeApp(tmp_path)
        policies_data = {
            "rules": [{"name": "dm_always", "conditions": {"is_dm": True}, "action": "always"}],
            "fallback": {"action": "selective"},
        }
        app.paths.policies_config.write_text(yaml.dump(policies_data))

        cmd = PoliciesCommand(app)
        cmd.execute(
            ParsedCommand(
                command="policies",
                subcommand="test",
                args=["+1234@s.whatsapp.net"],
                flags={"text": "hello there"},
            )
        )
