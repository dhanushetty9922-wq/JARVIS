"""JARVIS Main Entrypoint.

Starts JARVIS in Safe CLI mode:
1. Bootstraps configuration and directories
2. Initializes SQLite database and WAL mode
3. Instantiates Privacy and Permission Manager (Default: Zero-Trust BLOCKED)
4. Configures Central Security Manager and Confirmation Engine
5. Displays diagnostic health status report
6. Enters interactive safe command loop
"""

from __future__ import annotations

import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from config import settings
from core.assistant import JarvisAssistant
from core.command_router import CommandRouter

console = Console()

BANNER = """[bold cyan]
   ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
   ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
   ██║███████║██████╔╝██║   ██║██║███████╗
██  █║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
[/bold cyan]
[dim]Personal AI Computer Assistant — Windows Edition[/dim]
[green]Privacy-First • Local-First • Zero-Trust Security[/green]
"""


def render_status_table(report: dict) -> Table:
    """Render a clean Rich table summarizing JARVIS health and status."""
    table = Table(title="[bold yellow]JARVIS Core Diagnostics[/bold yellow]", show_header=True, header_style="bold magenta")
    table.add_column("Subsystem", style="cyan", width=24)
    table.add_column("State / Value", style="white")

    table.add_row("Core Status", "[bold green]ONLINE[/bold green]")
    table.add_row("Version", report["version"])
    table.add_row("Operating Mode", f"[bold]{report['operating_mode']}[/bold]")
    table.add_row("Safe Mode", "[bold green]ENABLED[/bold green]" if report["safe_mode"] == "ENABLED" else "[bold red]DISABLED[/bold red]")
    table.add_row("Emergency Stop", "[bold red]ACTIVE[/bold red]" if report["emergency_stopped"] else "[bold green]INACTIVE[/bold green]")
    table.add_row("Microphone Permission", "[bold green]ALLOWED[/bold green]" if report["microphone_permission"] == "ALLOWED" else "[bold red]BLOCKED[/bold red]")
    table.add_row("Internet Permission", "[bold green]ALLOWED[/bold green]" if report["internet_permission"] == "ALLOWED" else "[bold red]BLOCKED[/bold red]")
    table.add_row("Cloud AI Permission", "[bold green]ALLOWED[/bold green]" if report.get("cloud_ai_permission") == "ALLOWED" else "[bold red]BLOCKED[/bold red]")
    table.add_row("Memory Permission", "[bold green]ALLOWED[/bold green]" if report.get("memory_permission") == "ALLOWED" else "[bold red]BLOCKED[/bold red]")
    table.add_row("Long-Term Memory", report.get("memory_subsystem", "OFF"))
    table.add_row("Voice Subsystem", report["voice_subsystem"])
    table.add_row("AI Mode / Provider", f"{report.get('ai_mode', 'LOCAL')} | {report['ai_provider']}")
    table.add_row("AI Provider Status", f"[bold cyan]{report.get('ai_provider_available', 'OFFLINE')}[/bold cyan]")
    table.add_row("Process / System RAM", report.get("memory_usage", "N/A"))
    table.add_row("Database Engine", f"{report['database_status']}")
    table.add_row("Registered Approved Tools", str(report["registered_tools_count"]))
    table.add_row("Automation Engine", report["automation_subsystem"])

    return table


async def async_main() -> None:
    """Async main routine."""
    # 1. Initialize Assistant
    assistant = JarvisAssistant()
    router = CommandRouter(assistant)

    # 2. Check for CLI arguments like '--status'
    if len(sys.argv) > 1 and sys.argv[1] in ("--status", "status", "-s"):
        report = assistant.get_status_report()
        console.print(render_status_table(report))
        return

    # 3. Render Startup Banner & Status Table
    console.print(BANNER)
    report = assistant.get_status_report()
    console.print(render_status_table(report))
    console.print("\n[dim]Type [bold white]'help'[/bold white] for available commands, or [bold white]'exit'[/bold white] to quit.[/dim]\n")

    # 4. Interactive Command Loop
    loop = asyncio.get_event_loop()
    while True:
        try:
            # Non-blocking input prompt
            user_input = await loop.run_in_executor(None, input, "JARVIS > ")
            trimmed = user_input.strip()

            if not trimmed:
                continue

            if trimmed.lower() in ("exit", "quit", "q"):
                console.print("[yellow]Shutting down JARVIS. System going to sleep.[/yellow]")
                break

            response = await router.handle_command(trimmed)
            if response:
                console.print(response)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Keyboard interrupt received. Safe shutdown initiated.[/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Unexpected error:[/bold red] {e}")
    assistant.shutdown()


def main() -> None:
    """Entry point wrapper."""
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
