# Claude Otel Monitor

Claude Code API usage monitor via OpenTelemetry.

> **Note**: This project is merged from the original `jstat` scripts into a proper UV-managed Python package.

## Features

- **Today-only stats**: Default shows today's usage, with options for other dates
- **Call history**: View recent API calls with full details
- **Beautiful CLI**: Rich tables and formatted output
- **Model breakdown**: See usage by model (kimi, haiku, opus, etc.)
- **Cost tracking**: Track estimated costs in USD
- **Token usage**: Input/output/cache token counts
- **Easy management**: Start/stop collector with CLI commands

## Installation

```bash
cd claude-otel-monitor
uv sync
```

## Quick Start

### 1. Initialize

```bash
uv run python -m claude_otel_monitor.cli init
```

### 2. Start Collector

```bash
uv run python -m claude_otel_monitor.cli start
```

### 3. Configure Claude Code

Add to your shell profile (`~/.bashrc` or `~/.zshrc`):

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_METRICS_EXPORTER=otlp
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
export OTEL_METRIC_EXPORT_INTERVAL=10000
export OTEL_LOGS_EXPORT_INTERVAL=5000
```

Or set temporarily in current terminal:

```bash
source <(uv run python -m claude_otel_monitor.cli init)
```

### 4. Run Claude Code

```bash
claude
```

### 5. View Statistics

```bash
# Show today's stats (default)
uv run python -m claude_otel_monitor.cli stats

# Show all-time stats
uv run python -m claude_otel_monitor.cli stats --all

# Show specific date
uv run python -m claude_otel_monitor.cli stats -d 2026-02-22

# Show recent API calls (default: 20)
uv run python -m claude_otel_monitor.cli tail

# Show specific number of recent calls
uv run python -m claude_otel_monitor.cli tail -n 50
```

### 6. Stop Collector

```bash
uv run python -m claude_otel_monitor.cli stop
```

## Commands

| Command | Description |
|---------|-------------|
| `init` | Show setup instructions and check prerequisites |
| `start` | Start OpenTelemetry Collector |
| `stop` | Stop OpenTelemetry Collector |
| `stats` | Show API usage statistics (today by default) |
| `stats -a` | Show all-time statistics |
| `stats -d DATE` | Show statistics for specific date (YYYY-MM-DD) |
| `tail` | Show recent API calls (default: 20) |
| `tail -n N` | Show N recent API calls |

```bash
# Show help
uv run python -m claude_otel_monitor.cli --help

# Show specific command help
uv run python -m claude_otel_monitor.cli stats --help
```

## Example Output

### Stats (Today)

```
                    Claude Code API Usage Statistics (Today)
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Model                     ┃  Calls ┃        Input ┃       Output ┃     Cache R ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ claude-haiku-4-5-20251001 │      7 │          571 │          322 │         152 │
│ claude-sonnet-4-6         │     13 │         5887 │          115 │       32920 │
│ kimi-for-coding           │    179 │       374429 │        36156 │     1203348 │
└───────────────────────────┴────────┴──────────────┴──────────────┴─────────────┘

╭────────────────────────────────── Summary ───────────────────────────────────╮
│ Total Calls: 199                                                             │
│ Total Input: 380887 tokens                                                   │
│ Total Output: 36078 tokens                                                   │
│ Total Cost: $5.9621                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### Tail (Recent Calls)

```
                                   API Calls
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━┳━━━━━━━━━┓
┃ Time     ┃ Model                 ┃ Input ┃ Output ┃ Cache ┃  Cache ┃ Cost($) ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━╇━━━━━━━━━┩
│ 06:44:36 │ kimi-for-coding       │   222 │    139 │ 37632 │      0 │  0.0140 │
│ 06:44:45 │ kimi-for-coding       │  1691 │    276 │ 37632 │      0 │  0.0205 │
│ 06:44:47 │ kimi-for-coding       │   135 │     23 │   256 │      0 │  0.0003 │
└──────────┴───────────────────────┴───────┴────────┴───────┴────────┴─────────┘
```

## Project Structure

```
claude-otel-monitor/
├── src/claude_otel_monitor/
│   ├── __init__.py
│   ├── cli.py          # CLI entry point
│   ├── parser.py       # OTel metrics parser
│   ├── formatter.py    # Output formatting
│   └── tailer.py       # Real-time tailing
├── docker-compose.yml      # Collector setup
├── otel-collector-config.yaml  # Collector config
├── logrotate.conf          # Log rotation config (daily files)
├── metrics/                # Metrics data (symlink to ../jstat/metrics)
├── pyproject.toml
├── uv.lock
└── README.md
```

## Migration from jstat

This project replaces the original `jstat` scripts:

| Old (jstat) | New (claude-otel-monitor) |
|-------------|---------------------------|
| `analyze-metrics.py` | `uv run python -m claude_otel_monitor.cli stats` |
| `setup-claude-monitoring.sh` | `uv run python -m claude_otel_monitor.cli start` |
| `docker-compose.yml` | `uv run python -m claude_otel_monitor.cli start/stop` |

Data is shared via symlink at `metrics/` → `../jstat/metrics`.

## Log Rotation

To prevent the metrics file from growing too large, configure logrotate:

```bash
# Copy the config to logrotate.d
sudo cp logrotate.conf /etc/logrotate.d/claude-metrics

# Or run manually
logrotate -f logrotate.conf
```

This creates daily rotated files: `claude-metrics.json-20260223`, `claude-metrics.json-20260222.gz`, etc.

## License

MIT
