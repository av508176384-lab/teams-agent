from __future__ import annotations

import logging

import typer
import yaml
from rich.console import Console
from rich.table import Table

from teams_agent.config import load_config, load_env

app = typer.Typer(name="teams-agent", help="Teams auto-reply daemon with GPT and Telegram alerts")
ignore_app = typer.Typer(help="Manage the ignore list of contacts")
app.add_typer(ignore_app, name="ignore")

console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def start(verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging")) -> None:
    """Start the Teams monitoring daemon."""
    setup_logging(verbose)
    from teams_agent.daemon import Daemon

    daemon = Daemon()
    daemon.run()


@app.command()
def auth(verbose: bool = typer.Option(False, "--verbose", "-v")) -> None:
    """Authenticate with Microsoft Graph via browser SSO."""
    setup_logging(verbose)
    load_env()
    from teams_agent.graph_client import GraphClient

    client = GraphClient()
    console.print("[bold]Opening browser for authentication...[/]\n")
    result = client.authenticate_interactive()
    name = result.get("id_token_claims", {}).get("name", "Unknown")
    console.print(f"\n[bold green]Authenticated successfully as {name}![/]")
    console.print("Token cached for future use.")


@app.command()
def config() -> None:
    """Display current configuration."""
    cfg = load_config()
    console.print(yaml.dump(cfg, default_flow_style=False))


@app.command(name="test-telegram")
def test_telegram() -> None:
    """Send a test message via Telegram to verify setup."""
    load_env()
    from teams_agent.telegram_notifier import TelegramNotifier

    notifier = TelegramNotifier()
    if notifier.send_test():
        console.print("[bold green]Test message sent successfully![/]")
    else:
        console.print("[bold red]Failed to send test message. Check your TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.[/]")


@ignore_app.command("add")
def ignore_add(email: str = typer.Argument(help="Email or display name of contact to ignore")) -> None:
    """Add a contact to the ignore list."""
    from teams_agent.ignore_list import add_contact

    if add_contact(email):
        console.print(f"[green]Added {email} to ignore list.[/]")
    else:
        console.print(f"[yellow]{email} is already on the ignore list.[/]")


@ignore_app.command("remove")
def ignore_remove(email: str = typer.Argument(help="Email or display name to remove from ignore list")) -> None:
    """Remove a contact from the ignore list."""
    from teams_agent.ignore_list import remove_contact

    if remove_contact(email):
        console.print(f"[green]Removed {email} from ignore list.[/]")
    else:
        console.print(f"[yellow]{email} was not found on the ignore list.[/]")


@ignore_app.command("list")
def ignore_list() -> None:
    """Show all ignored contacts."""
    from teams_agent.ignore_list import get_ignored

    contacts = get_ignored()
    if not contacts:
        console.print("[dim]No contacts on the ignore list.[/]")
        return
    table = Table(title="Ignored Contacts")
    table.add_column("Email / Name", style="cyan")
    for c in contacts:
        table.add_row(c)
    console.print(table)


if __name__ == "__main__":
    app()
