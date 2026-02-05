"""wingman console - Launch interactive console."""

from wingman.cli.console import ConsoleApp


def console() -> None:
    """
    Launch the interactive Wingman console.

    Provides a REPL with /commands for managing configuration,
    contacts, policies, messaging, and bot lifecycle.
    """
    app = ConsoleApp()
    app.run()
