"""
Stats persistence — saves token/cost stats to ~/.habitly/stats.json
so data survives across Python process restarts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

_STATS_DIR = Path.home() / ".habitly"
_STATS_FILE = _STATS_DIR / "stats.json"


@dataclass
class DailyStats:
    date: str = field(default_factory=lambda: str(date.today()))
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    cache_writes: int = 0
    cache_reads: int = 0
    total_cost_usd: float = 0.0
    requests: int = 0

    @property
    def saved_by_cache_usd(self) -> float:
        # Full-price reads that were served from cache instead
        return self.cache_reads * 0.000003  # ~$3/1M avg input price


class StatsStore:
    """
    Persistent stats store. Call record() after every API response.
    Data is saved immediately to disk.

    Usage:
        store = StatsStore()
        store.record(response.usage, cost_usd=0.0042)
        print(store.today.summary)
    """

    def __init__(self) -> None:
        _STATS_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, DailyStats] = self._load()

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    @property
    def today(self) -> DailyStats:
        key = str(date.today())
        if key not in self._data:
            self._data[key] = DailyStats(date=key)
        return self._data[key]

    def record(self, usage: object, cost_usd: float = 0.0) -> None:
        s = self.today
        s.requests += 1
        s.total_input_tokens += getattr(usage, "input_tokens", 0) or 0
        s.total_output_tokens += getattr(usage, "output_tokens", 0) or 0
        s.cache_writes += getattr(usage, "cache_creation_input_tokens", 0) or 0
        s.cache_reads += getattr(usage, "cache_read_input_tokens", 0) or 0
        s.total_cost_usd += cost_usd
        self._save()

    def summary(self, days: int = 7) -> str:
        today_key = str(date.today())
        lines = [f"=== Habitly Stats ({days}d) ==="]
        for key in sorted(self._data)[-days:]:
            s = self._data[key]
            marker = " ← today" if key == today_key else ""
            lines.append(
                f"{s.date}{marker}: "
                f"{s.requests} req | "
                f"input {s.total_input_tokens:,} | "
                f"cache hit {s.cache_reads:,} | "
                f"${s.total_cost_usd:.4f}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _load(self) -> dict[str, DailyStats]:
        if not _STATS_FILE.exists():
            return {}
        try:
            raw = json.loads(_STATS_FILE.read_text())
            return {k: DailyStats(**v) for k, v in raw.items()}
        except Exception:
            return {}

    def _save(self) -> None:
        _STATS_FILE.write_text(json.dumps({k: asdict(v) for k, v in self._data.items()}, indent=2))
