"""Parse OpenTelemetry metrics from Claude Code."""

import json
from pathlib import Path
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Set, Optional


@dataclass
class ModelStats:
    """Statistics for a single model."""
    model: str
    count: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read: int = 0
    cache_creation: int = 0
    cost_usd: float = 0.0
    sessions: Set[str] = field(default_factory=set)


@dataclass
class ApiStats:
    """Overall API statistics."""
    models: Dict[str, ModelStats] = field(default_factory=dict)
    total_calls: int = 0
    total_input: int = 0
    total_output: int = 0
    total_cost: float = 0.0

    def get_or_create_model(self, model: str) -> ModelStats:
        if model not in self.models:
            self.models[model] = ModelStats(model=model)
        return self.models[model]


@dataclass
class ApiCall:
    """Single API call record."""
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_creation: int
    cost_usd: float
    session_id: str
    prompt_id: str


def parse_otl_file(filepath: Path, max_lines: int = 0) -> List[dict]:
    """Parse OpenTelemetry file (multi-line JSON).

    Args:
        filepath: Path to the metrics file
        max_lines: Maximum lines to read (0 = unlimited, for large files)
    """
    records = []
    try:
        with open(filepath, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if max_lines > 0 and line_num > max_lines:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (PermissionError, FileNotFoundError):
        pass
    return records


def get_file_line_count(filepath: Path) -> int:
    """Get number of lines in file efficiently."""
    count = 0
    try:
        with open(filepath, 'rb') as f:
            for _ in f:
                count += 1
    except (PermissionError, FileNotFoundError):
        pass
    return count


def parse_otl_file_last_n(filepath: Path, n: int) -> List[dict]:
    """Parse last N lines from file (efficient for large files)."""
    total_lines = get_file_line_count(filepath)
    skip_lines = max(0, total_lines - n)

    records = []
    try:
        with open(filepath, 'r') as f:
            for i, line in enumerate(f):
                if i < skip_lines:
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (PermissionError, FileNotFoundError):
        pass
    return records


def extract_stats(records: List[dict], date_filter: Optional[datetime] = None) -> ApiStats:
    """Extract API call statistics from records.

    Args:
        records: List of OTL records
        date_filter: If provided, only include calls from this date (local time)
    """
    stats = ApiStats()

    # Extract individual calls and filter by date if needed
    calls = extract_api_calls(records)

    if date_filter:
        # Filter to specific date (convert to local date for comparison)
        calls = [
            c for c in calls
            if c.timestamp.astimezone().date() == date_filter.date()
        ]

    # Aggregate from filtered calls
    for call in calls:
        model_stats = stats.get_or_create_model(call.model)
        model_stats.count += 1
        model_stats.input_tokens += call.input_tokens
        model_stats.output_tokens += call.output_tokens
        model_stats.cache_read += call.cache_read
        model_stats.cache_creation += call.cache_creation
        model_stats.cost_usd += call.cost_usd
        model_stats.sessions.add(call.session_id)

    # Calculate totals
    for model_stats in stats.models.values():
        stats.total_calls += model_stats.count
        stats.total_input += model_stats.input_tokens
        stats.total_output += model_stats.output_tokens
        stats.total_cost += model_stats.cost_usd

    return stats


def _process_token_metric(metric: dict, stats: ApiStats, session_id: str):
    """Process token usage metric."""
    sum_data = metric.get('sum', {})
    data_points = sum_data.get('dataPoints', [])

    for dp in data_points:
        dp_attrs = {
            a['key']: a['value'].get('stringValue', '')
            for a in dp.get('attributes', [])
        }
        token_type = dp_attrs.get('type', 'unknown')
        model = dp_attrs.get('model', 'unknown')
        value = int(dp.get('asDouble', dp.get('asInt', 0)))

        model_stats = stats.get_or_create_model(model)
        model_stats.sessions.add(session_id)

        if token_type == 'input':
            model_stats.input_tokens += value
        elif token_type == 'output':
            model_stats.output_tokens += value
        elif token_type == 'cacheRead':
            model_stats.cache_read += value
        elif token_type == 'cacheCreation':
            model_stats.cache_creation += value


def _process_cost_metric(metric: dict, stats: ApiStats, session_id: str):
    """Process cost metric."""
    sum_data = metric.get('sum', {})
    data_points = sum_data.get('dataPoints', [])

    for dp in data_points:
        dp_attrs = {
            a['key']: a['value'].get('stringValue', '')
            for a in dp.get('attributes', [])
        }
        model = dp_attrs.get('model', 'unknown')
        cost = float(dp.get('asDouble', 0))

        model_stats = stats.get_or_create_model(model)
        model_stats.cost_usd += cost
        model_stats.count += 1
        model_stats.sessions.add(session_id)


def extract_api_calls(records: List[dict]) -> List[ApiCall]:
    """Extract individual API calls from log records."""
    calls = []

    for record in records:
        if 'resourceLogs' not in record:
            continue

        for rl in record['resourceLogs']:
            for sl in rl.get('scopeLogs', []):
                for log in sl.get('logRecords', []):
                    body = log.get('body', {}).get('stringValue', '')
                    if body != 'claude_code.api_request':
                        continue

                    attrs = {
                        a['key']: _extract_value(a.get('value', {}))
                        for a in log.get('attributes', [])
                    }

                    # Parse timestamp
                    ts_str = attrs.get('event.timestamp', '')
                    try:
                        timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    except (ValueError, AttributeError):
                        # Fallback to timeUnixNano
                        nano = int(log.get('timeUnixNano', 0))
                        timestamp = datetime.fromtimestamp(nano / 1e9)

                    call = ApiCall(
                        timestamp=timestamp,
                        model=attrs.get('model', 'unknown'),
                        input_tokens=int(attrs.get('input_tokens', 0)),
                        output_tokens=int(attrs.get('output_tokens', 0)),
                        cache_read=int(attrs.get('cache_read_tokens', 0)),
                        cache_creation=int(attrs.get('cache_creation_tokens', 0)),
                        cost_usd=float(attrs.get('cost_usd', 0)),
                        session_id=attrs.get('session.id', 'unknown'),
                        prompt_id=attrs.get('prompt.id', 'unknown'),
                    )
                    calls.append(call)

    # Sort by timestamp
    calls.sort(key=lambda x: x.timestamp)
    return calls


def _extract_value(value_obj: dict) -> str:
    """Extract value from OTel value object."""
    if 'stringValue' in value_obj:
        return value_obj['stringValue']
    if 'intValue' in value_obj:
        return str(value_obj['intValue'])
    if 'doubleValue' in value_obj:
        return str(value_obj['doubleValue'])
    return ''
