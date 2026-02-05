"""Bot control commands."""

import asyncio
import time

from rich.console import Console

from wingman.core.rpc_client import RPCError

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import format_uptime, print_error, print_success

console = Console()


def _parse_duration(s: str) -> float | None:
    """Parse a duration string like '30m', '2h', '1d' to seconds."""
    s = s.strip().lower()
    if not s:
        return None
    try:
        if s.endswith("m"):
            return float(s[:-1]) * 60
        elif s.endswith("h"):
            return float(s[:-1]) * 3600
        elif s.endswith("d"):
            return float(s[:-1]) * 86400
        elif s.endswith("s"):
            return float(s[:-1])
        else:
            return float(s) * 60  # default to minutes
    except ValueError:
        return None


class BotCommand(BaseCommand):
    name = "start"
    description = "Start the bot"
    category = "Bot Control"
    subcommands = {}

    def execute(self, cmd: ParsedCommand) -> None:
        from wingman.daemon import DaemonManager

        paths = self.app.paths
        daemon = DaemonManager(paths)

        if daemon.is_running():
            pid = daemon.get_pid()
            console.print(f"[yellow]Wingman is already running (PID: {pid})[/yellow]")
            return

        # Check initialization
        if not paths.is_initialized():
            print_error("Wingman is not set up. Run 'wingman init' first.")
            return

        foreground = "f" in cmd.flags or "foreground" in cmd.flags

        if foreground:
            console.print("[blue]Starting Wingman in foreground...[/blue]")
            console.print("[dim]Press Ctrl+C to stop.[/dim]")
            try:
                from wingman.config.settings import Settings

                settings = Settings.load(paths=paths)
                errors = settings.validate()
                if errors:
                    for e in errors:
                        print_error(e)
                    return
                asyncio.run(self._run_foreground(settings))
            except KeyboardInterrupt:
                console.print("[yellow]Wingman stopped.[/yellow]")
            except Exception as e:
                print_error(f"Failed to start: {e}")
        else:
            console.print("[blue]Starting Wingman as background service...[/blue]")
            try:
                daemon.start()
                print_success("Wingman started.")
            except Exception as e:
                print_error(f"Failed to start: {e}")

    async def _run_foreground(self, settings):
        from wingman.core.agent import run_agent

        await run_agent(settings)


class StopCommand(BaseCommand):
    name = "stop"
    description = "Stop the bot"
    category = "Bot Control"

    def execute(self, cmd: ParsedCommand) -> None:
        from wingman.daemon import DaemonManager

        daemon = DaemonManager(self.app.paths)

        if not daemon.is_running():
            console.print("[yellow]Wingman is not running.[/yellow]")
            return

        pid = daemon.get_pid()
        console.print(f"[blue]Stopping Wingman (PID: {pid})...[/blue]")

        try:
            daemon.stop()
            print_success("Wingman stopped.")
        except Exception as e:
            print_error(f"Failed to stop: {e}")


class RestartCommand(BaseCommand):
    name = "restart"
    description = "Restart the bot"
    category = "Bot Control"

    def execute(self, cmd: ParsedCommand) -> None:
        from wingman.daemon import DaemonManager

        daemon = DaemonManager(self.app.paths)

        if not daemon.is_running():
            console.print("[yellow]Wingman is not running. Starting...[/yellow]")

        console.print("[blue]Restarting Wingman...[/blue]")
        try:
            daemon.restart()
            print_success("Wingman restarted.")
        except Exception as e:
            print_error(f"Failed to restart: {e}")


class StatusCommand(BaseCommand):
    name = "status"
    description = "Show bot status, uptime, transports"
    category = "Bot Control"

    def execute(self, cmd: ParsedCommand) -> None:
        from wingman.daemon import DaemonManager

        paths = self.app.paths
        daemon = DaemonManager(paths)

        console.print()

        if daemon.is_running():
            pid = daemon.get_pid()
            uptime = daemon.get_uptime()
            console.print(f"  Status:    [green]Running[/green] (PID: {pid})")
            console.print(f"  Uptime:    {format_uptime(uptime)}")

            # Try RPC for detailed status
            try:
                status = self.app.rpc.get_status()
                console.print(f"  Bot name:  {status.get('bot_name', '?')}")
                console.print(f"  Model:     {status.get('model', '?')}")
                paused = status.get("paused", False)
                if paused:
                    until = status.get("pause_until")
                    if until:
                        remaining = until - time.time()
                        if remaining > 0:
                            console.print(
                                f"  Paused:    [yellow]Yes[/yellow] ({format_uptime(remaining)} remaining)"
                            )
                        else:
                            console.print("  Paused:    [yellow]Yes (expired, pending auto-resume)[/yellow]")
                    else:
                        console.print("  Paused:    [yellow]Yes (indefinitely)[/yellow]")
                transports = status.get("transports", {})
                for name, info in transports.items():
                    st = "[green]active[/green]" if info.get("active") else "[red]inactive[/red]"
                    console.print(f"  Transport: {name} ({st})")
            except RPCError:
                if self.app.settings:
                    console.print(f"  Bot name:  {self.app.settings.bot_name}")
                    console.print(f"  Model:     {self.app.settings.openai_model}")
        else:
            console.print("  Status:    [dim]Not running[/dim]")
            if self.app.settings:
                console.print(f"  Bot name:  {self.app.settings.bot_name}")
                console.print(f"  Model:     {self.app.settings.openai_model}")

        console.print()


class PauseCommand(BaseCommand):
    name = "pause"
    description = "Temporarily pause bot responses"
    category = "Bot Control"

    def execute(self, cmd: ParsedCommand) -> None:
        duration = None
        if cmd.subcommand:
            duration = _parse_duration(cmd.subcommand)
            if duration is None:
                print_error(f"Invalid duration: {cmd.subcommand}")
                console.print("[dim]Examples: 30m, 2h, 1d[/dim]")
                return
        elif cmd.args:
            duration = _parse_duration(cmd.args[0])
            if duration is None:
                print_error(f"Invalid duration: {cmd.args[0]}")
                console.print("[dim]Examples: 30m, 2h, 1d[/dim]")
                return

        try:
            self.app.rpc.pause(duration)
            if duration:
                print_success(f"Bot paused for {format_uptime(duration)}.")
            else:
                print_success("Bot paused indefinitely. Use /resume to resume.")
        except RPCError as e:
            print_error(f"Failed to pause: {e}")


class ResumeCommand(BaseCommand):
    name = "resume"
    description = "Resume bot after pause"
    category = "Bot Control"

    def execute(self, cmd: ParsedCommand) -> None:
        try:
            self.app.rpc.resume()
            print_success("Bot resumed.")
        except RPCError as e:
            print_error(f"Failed to resume: {e}")
