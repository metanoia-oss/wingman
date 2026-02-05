"""Tests for the console command parser."""

from wingman.cli.console.parser import ParsedCommand, parse_input


class TestParseInput:
    def test_empty_input(self):
        assert parse_input("") is None
        assert parse_input("   ") is None

    def test_non_command_input(self):
        assert parse_input("hello world") is None
        assert parse_input("no slash here") is None

    def test_simple_command(self):
        cmd = parse_input("/help")
        assert cmd.command == "help"
        assert cmd.subcommand is None
        assert cmd.args == []
        assert cmd.flags == {}

    def test_command_with_subcommand(self):
        cmd = parse_input("/config show")
        assert cmd.command == "config"
        assert cmd.subcommand == "show"
        assert cmd.args == []

    def test_command_with_subcommand_and_args(self):
        cmd = parse_input("/config set openai.model gpt-4-turbo")
        assert cmd.command == "config"
        assert cmd.subcommand == "set"
        assert cmd.args == ["openai.model", "gpt-4-turbo"]

    def test_command_with_flags(self):
        cmd = parse_input("/contacts list --role friend")
        assert cmd.command == "contacts"
        assert cmd.subcommand == "list"
        assert cmd.flags == {"role": "friend"}

    def test_bool_flag(self):
        cmd = parse_input("/logs --error")
        assert cmd.command == "logs"
        assert cmd.flags["error"] is True

    def test_short_flag(self):
        cmd = parse_input("/logs -n 50")
        assert cmd.command == "logs"
        assert cmd.flags == {"n": "50"}

    def test_multiple_flags(self):
        cmd = parse_input("/contacts edit John --role friend --tone casual")
        assert cmd.command == "contacts"
        assert cmd.subcommand == "edit"
        assert cmd.args == ["John"]
        assert cmd.flags == {"role": "friend", "tone": "casual"}

    def test_quoted_string(self):
        cmd = parse_input('/send John "Hello World"')
        assert cmd.command == "send"
        assert "Hello World" in cmd.args

    def test_single_quoted_string(self):
        cmd = parse_input("/send John 'Hello World'")
        assert cmd.command == "send"
        assert "Hello World" in cmd.args

    def test_case_insensitive_command(self):
        cmd = parse_input("/HELP")
        assert cmd.command == "help"

    def test_case_insensitive_subcommand(self):
        cmd = parse_input("/CONFIG SHOW")
        assert cmd.command == "config"
        assert cmd.subcommand == "show"

    def test_leading_whitespace(self):
        cmd = parse_input("   /help")
        assert cmd.command == "help"

    def test_quit_exit_commands(self):
        cmd = parse_input("/quit")
        assert cmd.command == "quit"

        cmd = parse_input("/exit")
        assert cmd.command == "exit"


class TestParsedCommand:
    def test_defaults(self):
        cmd = ParsedCommand(command="test")
        assert cmd.command == "test"
        assert cmd.subcommand is None
        assert cmd.args == []
        assert cmd.flags == {}
