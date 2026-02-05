"""wingman status - Check bot status."""

import typer
from rich.console import Console
from rich.table import Table

from wingman.config.paths import WingmanPaths
from wingman.config.settings import Settings

console = Console()


def status() -> None:
    """
    Check the status of the Wingman bot.
    """
    paths = WingmanPaths()

    # Check initialization status
    is_initialized = paths.is_initialized()
    config_exists = paths.config_exists()

    # Create status table
    table = Table(title="Wingman Status", show_header=False, box=None)
    table.add_column("Item", style="bold")
    table.add_column("Status")

    # Setup status
    if is_initialized:
        table.add_row("Setup", "[green]Complete[/green]")
    elif config_exists:
        table.add_row("Setup", "[yellow]Partial (run wingman init)[/yellow]")
    else:
        table.add_row("Setup", "[red]Not initialized (run wingman init)[/red]")

    # Config location
    table.add_row("Config", str(paths.config_dir))

    # WhatsApp auth status
    has_auth = paths.auth_state_dir.exists() and any(paths.auth_state_dir.iterdir())
    if has_auth:
        table.add_row("WhatsApp", "[green]Connected[/green]")
    else:
        table.add_row("WhatsApp", "[yellow]Not connected (run wingman auth)[/yellow]")

    # Running status
    from wingman.daemon import DaemonManager
    daemon = DaemonManager(paths)

    if daemon.is_running():
        pid = daemon.get_pid()
        uptime = daemon.get_uptime()
        uptime_str = _format_uptime(uptime) if uptime else "unknown"
        table.add_row("Status", f"[green]Running[/green] (PID: {pid})")
        table.add_row("Uptime", uptime_str)
    else:
        table.add_row("Status", "[dim]Not running[/dim]")

    # Load settings for additional info
    if config_exists:
        try:
            settings = Settings.load(paths=paths)
            table.add_row("Bot Name", settings.bot_name)
            table.add_row("Model", settings.openai_model)
        except Exception:
            pass

    console.print()
    console.print(table)
    console.print()


def _format_uptime(seconds: float) -> str:
    """Format uptime in human-readable format."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        mins = int(seconds / 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds / 3600)
        mins = int((seconds % 3600) / 60)
        return f"{hours}h {mins}m"
