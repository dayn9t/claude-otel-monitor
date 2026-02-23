"""Format statistics for display."""

from typing import Dict, List
from rich.table import Table
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .parser import ApiStats, ModelStats, ApiCall


def format_number(n: int) -> str:
    """Format large numbers."""
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}G"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def create_stats_table(stats: ApiStats, title_suffix: str = "") -> Table:
    """Create a rich table with statistics."""
    table = Table(
        title=f"Claude Code API Usage Statistics{title_suffix}",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
    )

    table.add_column("Model", style="green", min_width=25)
    table.add_column("Calls", justify="right", style="yellow", min_width=6)
    table.add_column("Input", justify="right", style="cyan", min_width=12)
    table.add_column("Output", justify="right", style="cyan", min_width=12)
    table.add_column("Cache R", justify="right", style="dim cyan", min_width=12)
    table.add_column("Cache C", justify="right", style="dim cyan", min_width=12)
    table.add_column("Cost($)", justify="right", style="red", min_width=12)
    table.add_column("Sessions", justify="right", style="magenta", min_width=8)

    # Sort by model name
    for model_name in sorted(stats.models.keys()):
        data = stats.models[model_name]
        table.add_row(
            data.model,
            f"{data.count:,}",
            f"{data.input_tokens:,}",
            f"{data.output_tokens:,}",
            f"{data.cache_read:,}",
            f"{data.cache_creation:,}",
            f"${data.cost_usd:.4f}",
            str(len(data.sessions)),
        )

    # Add total row
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{stats.total_calls:,}[/bold]",
        f"[bold]{stats.total_input:,}[/bold]",
        f"[bold]{stats.total_output:,}[/bold]",
        "",
        "",
        f"[bold red]${stats.total_cost:.4f}[/bold red]",
        "",
    )

    return table


def create_summary_panel(stats: ApiStats) -> Panel:
    """Create a summary panel."""
    text = Text()
    text.append(f"Total Calls: ", style="bold")
    text.append(f"{stats.total_calls:,}\n", style="cyan")
    text.append(f"Total Input: ", style="bold")
    text.append(f"{stats.total_input:,} tokens\n", style="cyan")
    text.append(f"Total Output: ", style="bold")
    text.append(f"{stats.total_output:,} tokens\n", style="cyan")
    text.append(f"Total Cost: ", style="bold")
    text.append(f"${stats.total_cost:.4f}", style="red")

    return Panel(
        text,
        title="Summary",
        border_style="green",
    )


def print_stats(stats: ApiStats, console: Console = None, title_suffix: str = ""):
    """Print statistics to console."""
    if console is None:
        console = Console()

    if not stats.models:
        console.print("[yellow]No data available yet.[/yellow]")
        return

    table = create_stats_table(stats, title_suffix=title_suffix)
    summary = create_summary_panel(stats)

    console.print()
    console.print(table)
    console.print()
    console.print(summary)
    console.print()


def create_calls_table(calls: List[ApiCall]) -> Table:
    """Create a table for API calls."""
    table = Table(
        title="API Calls",
        title_style="bold cyan",
        show_header=True,
        header_style="bold magenta",
        border_style="blue",
    )

    table.add_column("Time", style="green", width=12)
    table.add_column("Model", style="cyan", width=25)
    table.add_column("Input", justify="right", style="yellow", width=10)
    table.add_column("Output", justify="right", style="yellow", width=10)
    table.add_column("Cache R", justify="right", style="dim cyan", width=10)
    table.add_column("Cache W", justify="right", style="dim cyan", width=10)
    table.add_column("Cost($)", justify="right", style="red", width=12)

    for call in calls:
        time_str = call.timestamp.strftime("%H:%M:%S")
        table.add_row(
            time_str,
            call.model,
            f"{call.input_tokens:,}",
            f"{call.output_tokens:,}",
            f"{call.cache_read:,}",
            f"{call.cache_creation:,}",
            f"{call.cost_usd:.4f}",
        )

    return table


def print_calls(calls: List[ApiCall], console: Console = None):
    """Print API calls to console."""
    if console is None:
        console = Console()

    if not calls:
        console.print("[yellow]No API calls found.[/yellow]")
        return

    table = create_calls_table(calls)
    console.print()
    console.print(table)
    console.print()
