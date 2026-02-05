"""wingman auth - WhatsApp authentication."""

import asyncio

import typer
from rich.console import Console
from rich.panel import Panel

from wingman.config.paths import WingmanPaths
from wingman.config.settings import Settings

console = Console()


def auth() -> None:
    """
    Connect to WhatsApp by scanning a QR code.

    Starts the WhatsApp listener in interactive mode to display
    the QR code for authentication.
    """
    paths = WingmanPaths()

    # Check if initialized
    if not paths.is_initialized():
        console.print("[red]Wingman is not set up yet.[/red]")
        console.print("Run [bold]wingman init[/bold] first.")
        raise typer.Exit(1)

    console.print(
        Panel.fit(
            "[bold blue]WhatsApp Authentication[/bold blue]\n\n"
            "A QR code will appear below.\n"
            "Scan it with WhatsApp on your phone:\n\n"
            "  1. Open WhatsApp\n"
            "  2. Go to Settings > Linked Devices\n"
            "  3. Tap 'Link a Device'\n"
            "  4. Scan the QR code",
            border_style="blue",
        )
    )
    console.print()

    # Load settings
    settings = Settings.load(paths=paths)

    # Run the auth process
    try:
        asyncio.run(_run_auth(settings))
    except KeyboardInterrupt:
        console.print()
        console.print("[yellow]Authentication cancelled.[/yellow]")
        raise typer.Exit(1)


async def _run_auth(settings: Settings) -> None:
    """Run the WhatsApp authentication process."""
    from wingman.core.transports import WhatsAppTransport

    connected = asyncio.Event()

    transport = WhatsAppTransport(settings.node_dir, auth_state_dir=settings.auth_state_dir)

    async def on_connected(user_id: str) -> None:
        console.print()
        console.print(f"[green]Connected as {user_id}[/green]")
        console.print()
        console.print("[bold green]Authentication successful![/bold green]")
        console.print("You can now run [bold]wingman start[/bold] to start the bot.")
        connected.set()

    async def on_qr_code() -> None:
        console.print("[dim]QR code displayed above - scan with WhatsApp[/dim]")

    transport.set_connected_handler(on_connected)
    transport.set_qr_code_handler(on_qr_code)

    # Start transport and wait for connection
    async def run_until_connected():
        asyncio.create_task(transport.start())
        try:
            # Wait for connection or timeout
            await asyncio.wait_for(connected.wait(), timeout=300)  # 5 minute timeout
        except asyncio.TimeoutError:
            console.print("[red]Authentication timed out.[/red]")
            console.print("Please try again with [bold]wingman auth[/bold]")
        finally:
            await transport.stop()

    await run_until_connected()
