"""wingman stop - Stop the bot."""

import typer
from rich.console import Console

from wingman.config.paths import WingmanPaths

console = Console()


def stop() -> None:
    """
    Stop the running Wingman bot.
    """
    paths = WingmanPaths()

    from wingman.daemon import DaemonManager

    daemon = DaemonManager(paths)

    if not daemon.is_running():
        console.print("[yellow]Wingman is not running.[/yellow]")
        raise typer.Exit()

    pid = daemon.get_pid()
    console.print(f"[blue]Stopping Wingman (PID: {pid})...[/blue]")

    try:
        daemon.stop()
        console.print("[green]Wingman stopped.[/green]")
    except Exception as e:
        console.print(f"[red]Failed to stop daemon: {e}[/red]")
        raise typer.Exit(1)
