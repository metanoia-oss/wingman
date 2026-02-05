"""Main CLI entry point for Wingman."""

import typer
from rich.console import Console

from wingman import __version__

from .commands import auth, config, console as console_cmd, init, logs, start, status, stop, uninstall

# Create main app
app = typer.Typer(
    name="wingman",
    help="Wingman - AI-powered personal chat agent for WhatsApp and iMessage",
    no_args_is_help=False,
    rich_markup_mode="rich",
)

# Rich console for pretty output
_console = Console()

# Add subcommands
app.command()(init.init)
app.command()(auth.auth)
app.command()(start.start)
app.command()(stop.stop)
app.command()(status.status)
app.command()(logs.logs)
app.command()(config.config)
app.command()(console_cmd.console)
app.command()(uninstall.uninstall)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit",
        is_eager=True,
    ),
) -> None:
    """Wingman - AI-powered personal chat agent."""
    if version:
        _console.print(f"Wingman v{__version__}")
        raise typer.Exit()

    # If no subcommand, launch interactive console
    if ctx.invoked_subcommand is None:
        from .console import ConsoleApp

        app = ConsoleApp()
        app.run()


if __name__ == "__main__":
    app()
