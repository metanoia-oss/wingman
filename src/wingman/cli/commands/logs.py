"""wingman logs - View bot logs."""

import subprocess
import sys

import typer
from rich.console import Console

from wingman.config.paths import WingmanPaths

console = Console()


def logs(
    follow: bool = typer.Option(
        True,
        "--follow/--no-follow",
        "-f/-F",
        help="Follow log output (stream new lines)",
    ),
    lines: int = typer.Option(
        50,
        "--lines",
        "-n",
        help="Number of lines to show",
    ),
    error: bool = typer.Option(
        False,
        "--error",
        "-e",
        help="Show error log instead of main log",
    ),
) -> None:
    """
    View Wingman activity logs.

    Streams the log file in real-time by default.
    Use --no-follow to just show recent lines.
    """
    paths = WingmanPaths()

    # Determine log file
    log_file = paths.log_dir / ("agent.log" if not error else "error.log")

    if not log_file.exists():
        console.print(f"[yellow]Log file not found: {log_file}[/yellow]")
        console.print("Wingman may not have run yet.")
        raise typer.Exit(1)

    console.print(f"[dim]Log file: {log_file}[/dim]")
    console.print()

    # Use tail to show/follow logs
    try:
        cmd = ["tail"]
        if follow:
            cmd.append("-f")
        cmd.extend(["-n", str(lines), str(log_file)])

        # Run tail and stream output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        try:
            for line in process.stdout:
                # Color-code log levels
                if "ERROR" in line:
                    console.print(f"[red]{line.rstrip()}[/red]")
                elif "WARNING" in line:
                    console.print(f"[yellow]{line.rstrip()}[/yellow]")
                elif "INFO" in line:
                    console.print(line.rstrip())
                else:
                    console.print(f"[dim]{line.rstrip()}[/dim]")
        except KeyboardInterrupt:
            process.terminate()
            console.print()

    except FileNotFoundError:
        console.print("[red]tail command not found[/red]")
        raise typer.Exit(1)
