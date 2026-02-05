"""wingman init - Interactive setup wizard."""


import typer
from rich.console import Console
from rich.panel import Panel

from wingman.cli.wizard import SetupWizard
from wingman.config.paths import WingmanPaths

console = Console()


def init(
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Overwrite existing configuration",
    ),
) -> None:
    """
    Interactive setup wizard for Wingman.

    Sets up OpenAI API key, bot personality, safety settings,
    and installs the WhatsApp listener.
    """
    console.print(
        Panel.fit(
            "[bold blue]Welcome to Wingman![/bold blue]\n\n"
            "This wizard will help you set up your personal AI chat agent.",
            border_style="blue",
        )
    )
    console.print()

    paths = WingmanPaths()

    # Check if already initialized
    if paths.is_initialized() and not force:
        console.print("[yellow]Wingman is already set up![/yellow]")
        console.print(f"Config location: {paths.config_dir}")
        console.print()
        console.print("To reconfigure, run: [bold]wingman init --force[/bold]")
        console.print("To connect WhatsApp, run: [bold]wingman auth[/bold]")
        console.print("To start the bot, run: [bold]wingman start[/bold]")
        raise typer.Exit()

    # Run setup wizard
    wizard = SetupWizard(paths, console)

    try:
        success = wizard.run()
        if success:
            console.print()
            console.print(
                Panel.fit(
                    "[bold green]Setup complete![/bold green]\n\n"
                    "Next steps:\n"
                    "  1. Run [bold]wingman auth[/bold] to connect WhatsApp\n"
                    "  2. Run [bold]wingman start[/bold] to start the bot",
                    border_style="green",
                )
            )
        else:
            console.print()
            console.print("[red]Setup incomplete. Please try again.[/red]")
            raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Setup cancelled.[/yellow]")
        raise typer.Exit(1)
