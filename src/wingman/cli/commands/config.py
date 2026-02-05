"""wingman config - Edit configuration."""

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.syntax import Syntax

from wingman.config.paths import WingmanPaths

console = Console()


def config(
    edit: bool = typer.Option(
        False,
        "--edit",
        "-e",
        help="Open config file in editor",
    ),
    show: bool = typer.Option(
        False,
        "--show",
        "-s",
        help="Show current config",
    ),
    path: bool = typer.Option(
        False,
        "--path",
        "-p",
        help="Show config file path",
    ),
) -> None:
    """
    View or edit Wingman configuration.

    Without options, shows an overview of config options.
    """
    paths = WingmanPaths()

    if not paths.config_exists():
        console.print("[red]Wingman is not set up yet.[/red]")
        console.print("Run [bold]wingman init[/bold] first.")
        raise typer.Exit(1)

    if path:
        console.print(str(paths.config_file))
        return

    if show:
        _show_config(paths)
        return

    if edit:
        _edit_config(paths)
        return

    # Default: show overview
    console.print("[bold]Wingman Configuration[/bold]")
    console.print()
    console.print(f"Config file: {paths.config_file}")
    console.print()
    console.print("Commands:")
    console.print("  [bold]wingman config --show[/bold]   Show current config")
    console.print("  [bold]wingman config --edit[/bold]   Open in editor")
    console.print("  [bold]wingman config --path[/bold]   Print config path")
    console.print()
    console.print("Config files:")
    console.print(f"  Main config:  {paths.config_file}")
    console.print(f"  Contacts:     {paths.contacts_config}")
    console.print(f"  Groups:       {paths.groups_config}")
    console.print(f"  Policies:     {paths.policies_config}")


def _show_config(paths: WingmanPaths) -> None:
    """Show the current config file contents."""
    config_file = paths.config_file

    if not config_file.exists():
        console.print("[yellow]Config file not found.[/yellow]")
        return

    with open(config_file, "r") as f:
        content = f.read()

    syntax = Syntax(content, "yaml", theme="monokai", line_numbers=True)
    console.print(syntax)


def _edit_config(paths: WingmanPaths) -> None:
    """Open config file in user's editor."""
    import os

    config_file = paths.config_file

    # Get editor from environment
    editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))

    console.print(f"[dim]Opening {config_file} in {editor}...[/dim]")

    try:
        subprocess.run([editor, str(config_file)], check=True)
    except FileNotFoundError:
        console.print(f"[red]Editor not found: {editor}[/red]")
        console.print("Set the EDITOR environment variable to your preferred editor.")
        raise typer.Exit(1)
    except subprocess.CalledProcessError as e:
        console.print(f"[red]Editor exited with error: {e}[/red]")
        raise typer.Exit(1)
