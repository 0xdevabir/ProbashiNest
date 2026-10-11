"""Per-client request limit, kept in memory (one process).

Every check costs LLM and speech calls, so one client must not be able to run
up the bill or crowd out other users.
"""
from __future__ import annotations

import math
import threading
import time
from collections import deque
from typing import Callable

from starlette.datastructures import Headers

MAX_TRACKED_CLIENTS = 10_000


class RateLimiter:
    def __init__(self, per_minute: int, *, window: float = 60.0, clock: Callable[[], float] = time.monotonic):
        self.limit = per_minute
        self.window = window
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> int:
        """Count one request. Returns 0 if allowed, else the seconds to wait."""
        if self.limit <= 0:
            return 0
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return max(1, math.ceil(self.window - (now - hits[0])))
            hits.append(now)
            if len(self._hits) > MAX_TRACKED_CLIENTS:
                self._forget_idle(now)
            return 0

    def _forget_idle(self, now: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]:
            del self._hits[key]


def client_key(scope, trust_proxy: bool) -> str:
    """Client address. X-Forwarded-For is believed only behind a proxy we control,
    and then only its last entry (the one our proxy added)."""
    if trust_proxy:
        forwarded = Headers(scope=scope).get("x-forwarded-for", "")
        last = forwarded.rsplit(",", 1)[-1].strip()
        if last:
            return last
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    """Limit POSTs to the given paths, before the upload is read."""

    def __init__(self, app, *, limiter: RateLimiter, paths: tuple[str, ...], trust_proxy: bool, on_limit):
        self.app = app
        self.limiter = limiter
        self.paths = paths
        self.trust_proxy = trust_proxy
        self.on_limit = on_limit  # seconds to wait -> ASGI response

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"] in self.paths:
            wait = self.limiter.check(client_key(scope, self.trust_proxy))
            if wait:
                return await self.on_limit(wait)(scope, receive, send)
        await self.app(scope, receive, send)
