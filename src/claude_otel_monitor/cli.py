"""CLI for Claude Code API monitor."""

import sys
from pathlib import Path

import click
from rich.console import Console

from .parser import parse_otl_file, extract_stats, extract_api_calls
from .formatter import print_stats, print_calls
from .tailer import MetricsTailer


# 默认使用项目目录下的 metrics（通过符号链接指向实际数据）
PROJECT_DIR = Path(__file__).parent.parent.parent
DEFAULT_METRICS_PATH = PROJECT_DIR / "metrics"


@click.group()
@click.option(
    "--metrics-path",
    "-p",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    default=DEFAULT_METRICS_PATH,
    help="Path to metrics directory",
)
@click.pass_context
def cli(ctx, metrics_path):
    """Claude Code API usage monitor via OpenTelemetry."""
    ctx.ensure_object(dict)
    ctx.obj["metrics_path"] = metrics_path
    ctx.obj["console"] = Console()


@cli.command()
@click.option(
    "--date",
    "-d",
    help="Date to show stats for (YYYY-MM-DD), default is today",
)
@click.option(
    "--all",
    "-a",
    is_flag=True,
    help="Show all-time statistics (ignore date filter)",
)
@click.pass_context
def stats(ctx, date, all):
    """Show API usage statistics (default: today only)."""
    metrics_path = ctx.obj["metrics_path"]
    console = ctx.obj["console"]

    import glob
    from datetime import datetime

    files = list(metrics_path.glob("*.json"))
    files.extend(metrics_path.glob("*.json.zst"))

    if not files:
        console.print(f"[red]No metrics files found in {metrics_path}[/red]")
        console.print("[yellow]Make sure collector is running and Claude Code is exporting metrics.[/yellow]")
        sys.exit(1)

    all_records = []
    for filepath in files:
        records = parse_otl_file(filepath)
        all_records.extend(records)

    # Determine date filter
    date_filter = None
    title_suffix = " (All Time)"
    if not all:
        if date:
            try:
                date_filter = datetime.strptime(date, "%Y-%m-%d")
                title_suffix = f" ({date})"
            except ValueError:
                console.print(f"[red]Invalid date format: {date}. Use YYYY-MM-DD[/red]")
                sys.exit(1)
        else:
            date_filter = datetime.now()
            title_suffix = " (Today)"

    api_stats = extract_stats(all_records, date_filter=date_filter)

    if not api_stats.models:
        if date_filter and not all:
            console.print(f"[yellow]No data found for {date_filter.strftime('%Y-%m-%d')}.[/yellow]")
        else:
            console.print("[yellow]No data available.[/yellow]")
        return

    print_stats(api_stats, console, title_suffix=title_suffix)


@cli.command()
@click.option(
    "-n",
    default=20,
    help="Number of calls to show",
    show_default=True,
)
@click.pass_context
def tail(ctx, n):
    """Show recent API calls."""
    metrics_path = ctx.obj["metrics_path"]
    console = ctx.obj["console"]

    import glob

    files = list(metrics_path.glob("*.json"))
    files.extend(metrics_path.glob("*.json.zst"))

    if not files:
        console.print(f"[red]No metrics files found in {metrics_path}[/red]")
        sys.exit(1)

    all_records = []
    for filepath in files:
        records = parse_otl_file(filepath)
        all_records.extend(records)

    calls = extract_api_calls(all_records)

    if not calls:
        console.print("[yellow]No API calls found.[/yellow]")
        return

    # Show last n calls
    recent_calls = calls[-n:]
    print_calls(recent_calls, console)


@cli.command()
@click.pass_context
def start(ctx):
    """Start OpenTelemetry Collector."""
    console = ctx.obj["console"]
    import shutil
    import subprocess

    # Check Docker
    if not shutil.which("docker"):
        console.print("[red]✗ Docker not found. Please install Docker.[/red]")
        sys.exit(1)

    docker_cmd = "docker compose" if shutil.which("docker") else None
    if not docker_cmd:
        console.print("[red]✗ docker compose not found.[/red]")
        sys.exit(1)

    # Check config files
    compose_file = PROJECT_DIR / "docker-compose.yml"
    if not compose_file.exists():
        console.print(f"[red]✗ docker-compose.yml not found in {PROJECT_DIR}[/red]")
        sys.exit(1)

    console.print("[cyan]=== Starting OpenTelemetry Collector ===[/cyan]\n")

    # Start collector
    try:
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "otel-collector"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            console.print("[green]✓ Collector started successfully[/green]")
            console.print("[dim]Metrics will be saved to:[/dim]", ctx.obj["metrics_path"])
        else:
            console.print(f"[red]✗ Failed to start collector:[/red]")
            console.print(result.stderr)
            sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def stop(ctx):
    """Stop OpenTelemetry Collector."""
    console = ctx.obj["console"]
    import subprocess

    console.print("[cyan]=== Stopping OpenTelemetry Collector ===[/cyan]\n")

    try:
        result = subprocess.run(
            ["docker", "compose", "down"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            console.print("[green]✓ Collector stopped[/green]")
        else:
            console.print(f"[yellow]Warning: {result.stderr}[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")


@cli.command()
@click.pass_context
def init(ctx):
    """Initialize monitoring setup."""
    console = ctx.obj["console"]

    console.print("[cyan]=== Claude Code OpenTelemetry Monitor Setup ===[/cyan]\n")

    # Check Docker
    import shutil

    if shutil.which("docker"):
        console.print("[green]✓ Docker found[/green]")
    else:
        console.print("[red]✗ Docker not found. Please install Docker.[/red]")
        sys.exit(1)

    # Create directories
    metrics_path = ctx.obj["metrics_path"]
    metrics_path.mkdir(parents=True, exist_ok=True)
    console.print(f"[green]✓ Metrics directory: {metrics_path}[/green]")

    # Show environment variables
    console.print("\n[cyan]Add these environment variables before running Claude Code:[/cyan]")
    console.print("""
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_METRIC_EXPORT_INTERVAL=10000
export OTEL_LOGS_EXPORT_INTERVAL=5000
""")

    console.print("[green]Setup complete![/green]")
    console.print("\n[dim]Next steps:[/dim]")
    console.print("  1. Run: [bold]uv run python -m claude_otel_monitor.cli start[/bold]")
    console.print("  2. Start Claude Code with the environment variables above")
    console.print("  3. Run: [bold]uv run python -m claude_otel_monitor.cli stats[/bold]")


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
