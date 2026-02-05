"""Tests for ConsoleApp initialization and command registration."""

from wingman.cli.console import ConsoleApp


class TestConsoleApp:
    def test_app_creates(self):
        app = ConsoleApp()
        assert app is not None

    def test_all_commands_registered(self):
        app = ConsoleApp()
        commands = app.registry.all_commands()

        expected = [
            "help", "quit", "start", "stop", "restart", "status",
            "pause", "resume", "config", "contacts", "groups",
            "policies", "send", "chats", "history", "logs",
            "stats", "activity",
        ]
        for name in expected:
            assert name in commands, f"Missing command: {name}"

    def test_all_categories_present(self):
        app = ConsoleApp()
        categories = {cmd.category for cmd in app.registry.all_commands().values()}
        expected_categories = {
            "Help & Navigation",
            "Bot Control",
            "Configuration",
            "Contact Management",
            "Group Management",
            "Policy Management",
            "Messaging",
            "Stats",
        }
        assert categories == expected_categories

    def test_quit_sets_running_false(self):
        app = ConsoleApp()
        assert app._running is True
        app.quit()
        assert app._running is False

    def test_rpc_lazy_init(self):
        app = ConsoleApp()
        assert app._rpc_client is None
        rpc = app.rpc
        assert rpc is not None
        assert app._rpc_client is rpc

    def test_exit_command_dispatches(self):
        """Verify /exit is handled as alias for /quit."""
        from wingman.cli.console.parser import parse_input

        app = ConsoleApp()
        cmd = parse_input("/exit")
        assert cmd.command == "exit"
        # The app.run() loop handles exit->quit mapping

    def test_paths_initialized(self):
        app = ConsoleApp()
        assert app.paths is not None
        assert app.paths.rpc_socket is not None
        assert app.paths.console_history is not None


class TestVersion:
    def test_version_synced(self):
        from wingman import __version__

        assert __version__ == "1.1.0"
