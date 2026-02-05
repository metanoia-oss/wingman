"""Interactive setup wizard for Wingman."""

import re

import questionary
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from wingman.config.paths import WingmanPaths
from wingman.installer import NodeInstaller


class SetupWizard:
    """Interactive setup wizard for Wingman."""

    def __init__(self, paths: WingmanPaths, console: Console):
        self.paths = paths
        self.console = console

    def run(self) -> bool:
        """Run the setup wizard. Returns True if setup completed successfully."""
        # Step 1: Check prerequisites
        if not self._check_prerequisites():
            return False

        # Step 2: OpenAI configuration
        api_key = self._get_openai_config()
        if not api_key:
            return False

        # Step 3: Bot personality
        bot_name, personality_desc, tone = self._get_personality_config()

        # Step 4: Safety settings
        safety_config = self._get_safety_config()

        # Step 5: Install Node.js listener
        if not self._install_node_listener():
            return False

        # Generate config files
        self._generate_configs(api_key, bot_name, personality_desc, tone, safety_config)

        return True

    def _check_prerequisites(self) -> bool:
        """Check system prerequisites."""
        self.console.print("[bold]Step 1/5: Checking prerequisites...[/bold]")
        self.console.print()

        installer = NodeInstaller(self.paths.node_dir)
        all_ok, issues = installer.check_prerequisites()

        # Python check (always passes if we're running)
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        self.console.print(f"  [green]✓[/green] Python {python_version}")

        # Node.js check
        version_info = installer.get_version_info()
        if version_info["node_version"]:
            self.console.print(f"  [green]✓[/green] Node.js {version_info['node_version']}")
        else:
            self.console.print("  [red]✗[/red] Node.js not found")

        # npm check
        if version_info["npm_version"]:
            self.console.print(f"  [green]✓[/green] npm {version_info['npm_version']}")
        else:
            self.console.print("  [red]✗[/red] npm not found")

        self.console.print()

        if not all_ok:
            self.console.print("[red]Prerequisites not met:[/red]")
            for issue in issues:
                self.console.print(f"  - {issue}")
            self.console.print()
            self.console.print("Please install the missing prerequisites and try again.")
            return False

        return True

    def _get_openai_config(self) -> str | None:
        """Get OpenAI API key from user."""
        self.console.print("[bold]Step 2/5: OpenAI Configuration[/bold]")
        self.console.print()

        api_key = questionary.password(
            "Enter your OpenAI API key:",
            instruction="(starts with 'sk-')"
        ).ask()

        if not api_key:
            return None

        # Validate API key format
        if not api_key.startswith("sk-"):
            self.console.print("[yellow]Warning: API key doesn't start with 'sk-'. Proceeding anyway.[/yellow]")

        # Optional: Test API key
        test = questionary.confirm(
            "Test API key?",
            default=True
        ).ask()

        if test:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=self.console,
            ) as progress:
                progress.add_task("Testing API key...", total=None)

                if self._test_api_key(api_key):
                    self.console.print("  [green]✓[/green] API key is valid")
                else:
                    self.console.print("  [red]✗[/red] API key test failed")
                    proceed = questionary.confirm(
                        "Continue anyway?",
                        default=False
                    ).ask()
                    if not proceed:
                        return None

        self.console.print()
        return api_key

    def _test_api_key(self, api_key: str) -> bool:
        """Test if the OpenAI API key is valid."""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            # Simple test - list models
            client.models.list()
            return True
        except Exception:
            return False

    def _get_personality_config(self) -> tuple[str, str, str]:
        """Get bot personality configuration."""
        self.console.print("[bold]Step 3/5: Bot Personality[/bold]")
        self.console.print()

        bot_name = questionary.text(
            "What should your bot be called?",
            default="Wingman"
        ).ask() or "Wingman"

        personality_desc = questionary.text(
            "Describe your bot's personality:",
            default="Witty and helpful assistant"
        ).ask() or "Witty and helpful assistant"

        tone = questionary.select(
            "Default tone:",
            choices=[
                questionary.Choice("casual - Relaxed and friendly", value="casual"),
                questionary.Choice("friendly - Warm and approachable", value="friendly"),
                questionary.Choice("professional - Polite and formal", value="professional"),
            ],
            default="casual"
        ).ask() or "casual"

        self.console.print()
        return bot_name, personality_desc, tone

    def _get_safety_config(self) -> dict:
        """Get safety settings configuration."""
        self.console.print("[bold]Step 4/5: Safety Settings[/bold]")
        self.console.print()

        max_replies = questionary.text(
            "Max replies per hour:",
            default="30",
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask() or "30"

        enable_quiet_hours = questionary.confirm(
            "Enable quiet hours?",
            default=True
        ).ask()

        quiet_start = 0
        quiet_end = 6

        if enable_quiet_hours:
            quiet_range = questionary.text(
                "Quiet hours (start-end, 24h format):",
                default="0-6",
                validate=lambda x: bool(re.match(r"^\d{1,2}-\d{1,2}$", x))
            ).ask() or "0-6"

            parts = quiet_range.split("-")
            quiet_start = int(parts[0])
            quiet_end = int(parts[1])

        self.console.print()

        return {
            "max_replies_per_hour": int(max_replies),
            "quiet_hours_enabled": enable_quiet_hours,
            "quiet_hours_start": quiet_start,
            "quiet_hours_end": quiet_end,
        }

    def _install_node_listener(self) -> bool:
        """Install the Node.js WhatsApp listener."""
        self.console.print("[bold]Step 5/5: Installing WhatsApp listener...[/bold]")
        self.console.print()

        installer = NodeInstaller(self.paths.node_dir)

        # Check if already installed
        if installer.is_installed():
            self.console.print("  [green]✓[/green] Node.js listener already installed")
            self.console.print()
            return True

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            task = progress.add_task("Installing...", total=None)

            def update_progress(step: str, message: str):
                progress.update(task, description=message)

            success = installer.install(progress_callback=update_progress)

        if success:
            self.console.print("  [green]✓[/green] Node.js listener installed")
        else:
            self.console.print("  [red]✗[/red] Installation failed")

        self.console.print()
        return success

    def _generate_configs(
        self,
        api_key: str,
        bot_name: str,
        personality_desc: str,
        tone: str,
        safety_config: dict
    ) -> None:
        """Generate configuration files."""
        # Ensure directories exist
        self.paths.ensure_directories()

        # Main config
        config = {
            "bot": {
                "name": bot_name,
            },
            "openai": {
                "api_key": api_key,
                "model": "gpt-4o",
                "max_response_tokens": 150,
                "temperature": 0.8,
            },
            "personality": {
                "base_prompt": f"You are {bot_name}, a {personality_desc}.",
                "default_tone": tone,
            },
            "safety": {
                "max_replies_per_hour": safety_config["max_replies_per_hour"],
                "cooldown_seconds": 60,
                "quiet_hours": {
                    "enabled": safety_config["quiet_hours_enabled"],
                    "start": safety_config["quiet_hours_start"],
                    "end": safety_config["quiet_hours_end"],
                },
            },
        }

        with open(self.paths.config_file, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Contacts config (template)
        contacts_config = {
            "contacts": {
                "# Add contacts here using their JID": {
                    "name": "Example Contact",
                    "role": "friend",
                    "tone": "casual",
                }
            },
            "defaults": {
                "role": "unknown",
                "tone": "neutral",
                "allow_proactive": False,
            }
        }

        # Remove the comment key (it was just for illustration)
        contacts_config["contacts"] = {}

        with open(self.paths.contacts_config, "w") as f:
            yaml.dump(contacts_config, f, default_flow_style=False, sort_keys=False)
            f.write("\n# Add contacts like this:\n")
            f.write("# contacts:\n")
            f.write('#   "+14155551234@s.whatsapp.net":\n')
            f.write("#     name: John\n")
            f.write("#     role: friend  # girlfriend, sister, friend, family, colleague, unknown\n")
            f.write("#     tone: casual  # affectionate, loving, friendly, casual, sarcastic, neutral\n")

        # Groups config (template)
        groups_config = {
            "groups": {},
            "defaults": {
                "category": "unknown",
                "reply_policy": "selective",
            }
        }

        with open(self.paths.groups_config, "w") as f:
            yaml.dump(groups_config, f, default_flow_style=False, sort_keys=False)
            f.write("\n# Add groups like this:\n")
            f.write("# groups:\n")
            f.write('#   "120363012345678901@g.us":\n')
            f.write("#     name: Family Chat\n")
            f.write("#     category: family  # family, friends, work, unknown\n")
            f.write("#     reply_policy: always  # always, selective, never\n")

        # Policies config (template)
        policies_config = {
            "rules": [
                {
                    "name": "dm_always",
                    "conditions": {
                        "is_dm": True,
                    },
                    "action": "always",
                },
                {
                    "name": "group_selective",
                    "conditions": {
                        "is_group": True,
                    },
                    "action": "selective",
                },
            ],
            "fallback": {
                "action": "selective",
            }
        }

        with open(self.paths.policies_config, "w") as f:
            yaml.dump(policies_config, f, default_flow_style=False, sort_keys=False)

        self.console.print(f"[dim]Config saved to {self.paths.config_dir}[/dim]")
