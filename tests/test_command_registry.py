"""Tests for the command registry."""

from wingman.cli.console.command_registry import BaseCommand, CommandRegistry
from wingman.cli.console.parser import ParsedCommand


class MockApp:
    """Minimal mock for ConsoleApp."""
    pass


class SampleCommand(BaseCommand):
    name = "test"
    description = "A test command"
    category = "Test"
    subcommands = {"sub1": "Subcommand 1", "sub2": "Subcommand 2"}

    def execute(self, cmd: ParsedCommand) -> None:
        self._last_cmd = cmd


class FailCommand(BaseCommand):
    name = "fail"
    description = "A command that raises"
    category = "Test"

    def execute(self, cmd: ParsedCommand) -> None:
        raise ValueError("Intentional error")


class TestCommandRegistry:
    def setup_method(self):
        self.registry = CommandRegistry()
        self.app = MockApp()

    def test_register_and_get(self):
        cmd = SampleCommand(self.app)
        self.registry.register(cmd)
        assert self.registry.get("test") is cmd

    def test_get_missing(self):
        assert self.registry.get("nonexistent") is None

    def test_dispatch_found(self):
        cmd = SampleCommand(self.app)
        self.registry.register(cmd)
        parsed = ParsedCommand(command="test", subcommand="sub1")
        assert self.registry.dispatch(parsed) is True
        assert cmd._last_cmd is parsed

    def test_dispatch_not_found(self):
        parsed = ParsedCommand(command="nonexistent")
        assert self.registry.dispatch(parsed) is False

    def test_dispatch_handles_error(self):
        cmd = FailCommand(self.app)
        self.registry.register(cmd)
        parsed = ParsedCommand(command="fail")
        # Should not raise, error is caught
        assert self.registry.dispatch(parsed) is True

    def test_all_commands(self):
        self.registry.register(SampleCommand(self.app))
        self.registry.register(FailCommand(self.app))
        all_cmds = self.registry.all_commands()
        assert "test" in all_cmds
        assert "fail" in all_cmds

    def test_get_completions(self):
        self.registry.register(SampleCommand(self.app))
        completions = self.registry.get_completions()
        assert "/test" in completions

    def test_get_subcommand_completions(self):
        self.registry.register(SampleCommand(self.app))
        subs = self.registry.get_subcommand_completions("test")
        assert "sub1" in subs
        assert "sub2" in subs

    def test_get_subcommand_completions_no_subs(self):
        self.registry.register(FailCommand(self.app))
        subs = self.registry.get_subcommand_completions("fail")
        assert subs == []

    def test_get_subcommand_completions_missing(self):
        subs = self.registry.get_subcommand_completions("nonexistent")
        assert subs == []


class TestBaseCommand:
    def test_get_info(self):
        cmd = SampleCommand(MockApp())
        info = cmd.get_info()
        assert info.name == "test"
        assert info.description == "A test command"
        assert info.category == "Test"
        assert "sub1" in info.subcommands
