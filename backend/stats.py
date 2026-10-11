"""Aggregate counters for the impact page. Counts only: no text, no names, no addresses.

Kept in memory, so they restart from zero with the process and are per worker.
"""
from __future__ import annotations

import threading
from collections import Counter
from datetime import datetime, timezone


class Stats:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._since = datetime.now(timezone.utc)
            self._levels: Counter[str] = Counter()
            self._codes: Counter[str] = Counter()
            self._countries: Counter[str] = Counter()
            self._channels: Counter[str] = Counter()
            self._reports = 0

    def record_check(self, *, channel: str, level: str, codes: list[str], country: str | None) -> None:
        # The country comes from a document, so only a plain two-letter code is counted.
        country = (country or "").strip().upper()
        with self._lock:
            self._levels[level] += 1
            self._channels[channel] += 1
            self._codes.update(list(dict.fromkeys(codes)))  # each code once per check, in a stable order
            if len(country) == 2 and country.isascii() and country.isalpha():
                self._countries[country] += 1

    def record_report(self) -> None:
        with self._lock:
            self._reports += 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "since": self._since.isoformat(timespec="seconds"),
                "checks": sum(self._levels.values()),
                "by_level": {level: self._levels[level] for level in ("red", "amber", "green")},
                "by_channel": dict(self._channels),
                "by_country": dict(self._countries.most_common()),
                "top_reasons": [{"code": c, "count": n} for c, n in self._codes.most_common(10)],
                "reports": self._reports,
            }


STATS = Stats()
