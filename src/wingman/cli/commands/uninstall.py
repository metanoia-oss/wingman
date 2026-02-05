"""wingman uninstall - Remove Wingman completely."""

import shutil

import typer
from rich.console import Console

from wingman.config.paths import WingmanPaths

console = Console()


def uninstall(
    keep_config: bool = typer.Option(
        False,
        "--keep-config",
        "-k",
        help="Keep configuration files (only remove data and stop daemon)",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Don't ask for confirmation",
    ),
) -> None:
    """
    Uninstall Wingman and remove all data.

    This will:
    - Stop the running daemon
    - Remove the launchd service (macOS)
    - Remove config files (unless --keep-config)
    - Remove data files (database, auth state)
    - Remove log files

    After running this, you can run `pip uninstall wingman-ai` to
    remove the package itself.
    """
    paths = WingmanPaths()

    # Show what will be removed
    console.print("[bold]This will remove:[/bold]")
    console.print()

    if not keep_config:
        console.print(f"  Config:  {paths.config_dir}")
    console.print(f"  Data:    {paths.data_dir}")
    console.print(f"  Logs:    {paths.cache_dir}")

    if paths.launchd_plist.exists():
        console.print(f"  Service: {paths.launchd_plist}")

    console.print()

    # Confirm
    if not force:
        confirm = typer.confirm("Are you sure you want to uninstall Wingman?")
        if not confirm:
            console.print("[yellow]Uninstall cancelled.[/yellow]")
            raise typer.Exit()

    # Stop daemon first
    from wingman.daemon import DaemonManager

    daemon = DaemonManager(paths)

    if daemon.is_running():
        console.print("[blue]Stopping daemon...[/blue]")
        try:
            daemon.stop()
        except Exception as e:
            console.print(f"[yellow]Warning: Could not stop daemon: {e}[/yellow]")

    # Remove launchd service
    daemon.uninstall()

    # Remove directories
    removed = []

    if not keep_config and paths.config_dir.exists():
        try:
            shutil.rmtree(paths.config_dir)
            removed.append("config")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove config: {e}[/yellow]")

    if paths.data_dir.exists():
        try:
            shutil.rmtree(paths.data_dir)
            removed.append("data")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove data: {e}[/yellow]")

    if paths.cache_dir.exists():
        try:
            shutil.rmtree(paths.cache_dir)
            removed.append("logs")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove logs: {e}[/yellow]")

    console.print()
    console.print("[green]Wingman uninstalled successfully.[/green]")

    if removed:
        console.print(f"Removed: {', '.join(removed)}")

    if keep_config:
        console.print(f"[dim]Config preserved at: {paths.config_dir}[/dim]")

    console.print()
    console.print("To remove the package, run:")
    console.print("  [bold]pip uninstall wingman-ai[/bold]")
