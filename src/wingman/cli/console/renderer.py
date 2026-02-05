"""Rich output helpers for the interactive console."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]{message}[/red]")


def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[yellow]{message}[/yellow]")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]{message}[/green]")


def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[blue]{message}[/blue]")


def print_dim(message: str) -> None:
    """Print dimmed text."""
    console.print(f"[dim]{message}[/dim]")


def print_yaml(content: str, title: str | None = None) -> None:
    """Print syntax-highlighted YAML."""
    syntax = Syntax(content, "yaml", theme="monokai", line_numbers=False)
    if title:
        console.print(Panel(syntax, title=title, border_style="blue"))
    else:
        console.print(syntax)


def print_panel(content: str, title: str | None = None, border_style: str = "blue") -> None:
    """Print content in a panel."""
    console.print(Panel(content, title=title, border_style=border_style))


def make_table(
    title: str, columns: list[tuple[str, str]], rows: list[list[str]], show_lines: bool = False
) -> None:
    """Create and print a Rich table.

    Args:
        title: Table title
        columns: List of (name, style) tuples
        rows: List of row data (each row is a list of strings)
        show_lines: Whether to show lines between rows
    """
    table = Table(title=title, show_lines=show_lines)
    for name, style in columns:
        table.add_column(name, style=style)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def format_uptime(seconds: float | None) -> str:
    """Format uptime in human-readable format."""
    if seconds is None:
        return "unknown"
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
