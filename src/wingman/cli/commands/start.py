"""wingman start - Start the bot."""

import asyncio
import sys

import typer
from rich.console import Console
from rich.panel import Panel

from wingman.config.paths import WingmanPaths
from wingman.config.settings import Settings

console = Console()


def start(
    foreground: bool = typer.Option(
        False,
        "--foreground",
        "-f",
        help="Run in foreground instead of as daemon",
    ),
) -> None:
    """
    Start the Wingman bot.

    By default, starts as a background daemon (macOS launchd).
    Use --foreground to run in the current terminal.
    """
    paths = WingmanPaths()

    # Check if initialized
    if not paths.is_initialized():
        console.print("[red]Wingman is not set up yet.[/red]")
        console.print("Run [bold]wingman init[/bold] first.")
        raise typer.Exit(1)

    # Check if auth state exists
    if not paths.auth_state_dir.exists() or not any(paths.auth_state_dir.iterdir()):
        console.print("[red]WhatsApp is not connected.[/red]")
        console.print("Run [bold]wingman auth[/bold] first.")
        raise typer.Exit(1)

    # Load settings
    settings = Settings.load(paths=paths)

    # Validate settings
    errors = settings.validate()
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for error in errors:
            console.print(f"  - {error}")
        raise typer.Exit(1)

    if foreground:
        # Run in foreground
        console.print(Panel.fit(
            "[bold blue]Starting Wingman[/bold blue]\n\n"
            f"Bot name: {settings.bot_name}\n"
            f"Model: {settings.openai_model}\n\n"
            "Press Ctrl+C to stop.",
            border_style="blue",
        ))
        console.print()

        try:
            asyncio.run(_run_foreground(settings))
        except KeyboardInterrupt:
            console.print()
            console.print("[yellow]Wingman stopped.[/yellow]")
    else:
        # Start as daemon
        _start_daemon(paths, settings)


async def _run_foreground(settings: Settings) -> None:
    """Run the bot in foreground mode."""
    from wingman.core.agent import run_agent
    await run_agent(settings)


def _start_daemon(paths: WingmanPaths, settings: Settings) -> None:
    """Start the bot as a background daemon."""
    from wingman.daemon import DaemonManager

    daemon = DaemonManager(paths)

    # Check if already running
    if daemon.is_running():
        pid = daemon.get_pid()
        console.print(f"[yellow]Wingman is already running (PID: {pid})[/yellow]")
        console.print("Run [bold]wingman stop[/bold] to stop it first.")
        raise typer.Exit(1)

    # Start daemon
    console.print("[blue]Starting Wingman as background service...[/blue]")

    try:
        daemon.start()
        console.print()
        console.print("[green]Wingman started as background service.[/green]")
        console.print()
        console.print("Commands:")
        console.print("  [bold]wingman status[/bold]  - Check if running")
        console.print("  [bold]wingman logs[/bold]    - View activity logs")
        console.print("  [bold]wingman stop[/bold]    - Stop the bot")
    except Exception as e:
        console.print(f"[red]Failed to start daemon: {e}[/red]")
        raise typer.Exit(1)
