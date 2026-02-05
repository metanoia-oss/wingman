"""Configuration commands."""

import os
import subprocess

import yaml
from rich.console import Console

from wingman.config.yaml_writer import read_yaml, set_nested_value, write_yaml

from ..command_registry import BaseCommand
from ..parser import ParsedCommand
from ..renderer import print_error, print_success, print_yaml

console = Console()


class ConfigCommand(BaseCommand):
    name = "config"
    description = "View or modify configuration"
    category = "Configuration"
    subcommands = {
        "show": "Show config (optionally filter: openai, safety, bot, imessage)",
        "set": "Set a value (e.g., /config set openai.model gpt-4-turbo)",
        "edit": "Open config in $EDITOR",
        "reload": "Force reload all configs",
    }

    def execute(self, cmd: ParsedCommand) -> None:
        if cmd.subcommand == "show":
            self._show(cmd)
        elif cmd.subcommand == "set":
            self._set(cmd)
        elif cmd.subcommand == "edit":
            self._edit()
        elif cmd.subcommand == "reload":
            self._reload()
        else:
            self._show(cmd)

    def _show(self, cmd: ParsedCommand) -> None:
        config_file = self.app.paths.config_file
        if not config_file.exists():
            print_error("Config file not found. Run 'wingman init' first.")
            return

        data = read_yaml(config_file)
        if not data:
            print_error("Config file is empty or malformed.")
            return

        section = cmd.args[0] if cmd.args else None

        if section:
            if section in data:
                content = yaml.dump(
                    {section: data[section]}, default_flow_style=False, sort_keys=False
                )
            else:
                print_error(f"Unknown section: {section}")
                console.print(f"[dim]Available: {', '.join(data.keys())}[/dim]")
                return
        else:
            # Mask API key for display
            display_data = dict(data)
            openai_section = display_data.get("openai")
            if isinstance(openai_section, dict) and "api_key" in openai_section:
                key = openai_section.get("api_key", "")
                if isinstance(key, str) and len(key) > 8:
                    display_data["openai"] = dict(openai_section)
                    display_data["openai"]["api_key"] = key[:4] + "..." + key[-4:]
            content = yaml.dump(display_data, default_flow_style=False, sort_keys=False)

        print_yaml(content, title="Configuration")

    def _set(self, cmd: ParsedCommand) -> None:
        if len(cmd.args) < 2:
            print_error("Usage: /config set <key> <value>")
            console.print("[dim]Example: /config set openai.model gpt-4-turbo[/dim]")
            return

        key = cmd.args[0]
        value = " ".join(cmd.args[1:])

        config_file = self.app.paths.config_file
        if not config_file.exists():
            print_error("Config file not found. Run 'wingman init' first.")
            return

        data = read_yaml(config_file)
        set_nested_value(data, key, value)
        write_yaml(config_file, data)

        print_success(f"Set {key} = {value}")
        console.print("[dim]Changes will be picked up within 2 seconds.[/dim]")

    def _edit(self) -> None:
        config_file = self.app.paths.config_file
        if not config_file.exists():
            print_error("Config file not found. Run 'wingman init' first.")
            return

        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "nano"))
        console.print(f"[dim]Opening {config_file} in {editor}...[/dim]")

        try:
            subprocess.run([editor, str(config_file)], check=True)
        except FileNotFoundError:
            print_error(f"Editor not found: {editor}")
            console.print("[dim]Set EDITOR environment variable.[/dim]")
        except subprocess.CalledProcessError as e:
            print_error(f"Editor exited with error: {e}")

    def _reload(self) -> None:
        try:
            self.app.settings = None
            if self.app.paths.config_exists():
                from wingman.config.settings import Settings

                self.app.settings = Settings.load(paths=self.app.paths)
            print_success("Configuration reloaded.")
        except Exception as e:
            print_error(f"Failed to reload: {e}")
