"""Tail metrics files in real-time."""

import time
import glob
from pathlib import Path
from typing import Callable, Optional
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

from .parser import parse_otl_file, extract_stats
from .formatter import print_stats


class MetricsTailer:
    """Tail metrics files and display updates."""

    def __init__(self, metrics_path: Path, console: Console = None):
        self.metrics_path = Path(metrics_path)
        self.console = console or Console()
        self._running = False
        self._last_size = 0

    def find_files(self) -> list:
        """Find all metrics files."""
        patterns = [
            str(self.metrics_path / "*.json"),
            str(self.metrics_path / "*.json.zst"),
        ]
        files = []
        for pattern in patterns:
            files.extend(glob.glob(pattern))
        return files

    def read_all_records(self) -> list:
        """Read all records from all files."""
        files = self.find_files()
        all_records = []
        for filepath in files:
            records = parse_otl_file(Path(filepath))
            all_records.extend(records)
        return all_records

    def tail(
        self,
        interval: float = 5.0,
        on_update: Optional[Callable] = None,
    ):
        """Tail metrics files and display updates."""
        self._running = True

        with Live(
            Spinner("dots", text="Waiting for metrics..."),
            console=self.console,
            refresh_per_second=4,
        ) as live:
            while self._running:
                records = self.read_all_records()

                if records:
                    stats = extract_stats(records)

                    # Create display
                    from rich.table import Table
                    from .formatter import create_stats_table, create_summary_panel

                    if stats.models:
                        table = create_stats_table(stats)
                        summary = create_summary_panel(stats)

                        live.update(table)
                        live.console.print()
                        live.console.print(summary)

                        if on_update:
                            on_update(stats)
                    else:
                        live.update("[yellow]No metrics data found in files.[/yellow]")
                else:
                    live.update(
                        f"[dim]Waiting for metrics in {self.metrics_path}...[/dim]"
                    )

                time.sleep(interval)

    def stop(self):
        """Stop tailing."""
        self._running = False

    def tail_once(self):
        """Display current stats once (for initial display)."""
        records = self.read_all_records()
        if records:
            stats = extract_stats(records)
            print_stats(stats, self.console)
        else:
            self.console.print(f"[yellow]No metrics files found in {self.metrics_path}[/yellow]")
