"""Log viewing command."""

import subprocess

from rich.console import Console

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import print_error

console = Console()


class LogsCommand(BaseCommand):
    name = "logs"
    description = "View bot activity logs"
    category = "Bot Control"
    usage = "/logs [-n lines] [--follow|-f] [--error]"
    examples = [
        "/logs",
        "/logs -n 100",
        "/logs --follow",
        "/logs -f",
        "/logs --error",
    ]
    subcommands = {}

    def execute(self, cmd: ParsedCommand) -> None:
        lines = 50
        show_error = False
        follow = "follow" in cmd.flags or "f" in cmd.flags

        if "n" in cmd.flags:
            try:
                lines = int(cmd.flags["n"])
            except (ValueError, TypeError):
                pass

        if "error" in cmd.flags:
            show_error = True

        log_name = "error.log" if show_error else "agent.log"
        log_file = self.app.paths.log_dir / log_name

        if not log_file.exists():
            console.print(f"[dim]Log file not found: {log_file}[/dim]")
            console.print("[dim]Wingman may not have run yet.[/dim]")
            return

        console.print(f"[dim]Log file: {log_file}[/dim]")
        if follow:
            console.print("[dim]Streaming logs... Press Ctrl+C to stop.[/dim]")
        console.print()

        if follow:
            self._stream_logs(log_file, lines)
        else:
            self._show_logs(log_file, lines)

    def _show_logs(self, log_file, lines: int) -> None:
        """Show a snapshot of recent log lines."""
        try:
            result = subprocess.run(
                ["tail", "-n", str(lines), str(log_file)],
                capture_output=True,
                text=True,
            )
            self._print_lines(result.stdout)
        except FileNotFoundError:
            print_error("tail command not found")

    def _stream_logs(self, log_file, lines: int) -> None:
        """Stream log output using tail -f in a thread."""
        try:
            process = subprocess.Popen(
                ["tail", "-f", "-n", str(lines), str(log_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            try:
                for line in process.stdout:
                    self._print_line(line.rstrip())
            except KeyboardInterrupt:
                pass
            finally:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                console.print()
                console.print("[dim]Log streaming stopped.[/dim]")

        except FileNotFoundError:
            print_error("tail command not found")

    def _print_lines(self, output: str) -> None:
        """Print log output with color coding."""
        for line in output.splitlines():
            self._print_line(line)

    def _print_line(self, line: str) -> None:
        """Print a single log line with color coding."""
        if "ERROR" in line:
            console.print(f"[red]{line}[/red]")
        elif "WARNING" in line:
            console.print(f"[yellow]{line}[/yellow]")
        elif "INFO" in line:
            console.print(line)
        else:
            console.print(f"[dim]{line}[/dim]")
