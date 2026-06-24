import time
from collections import defaultdict, deque
from threading import Lock

from app.config import settings
from app.errors import rate_limited


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        cutoff = now - self.window_seconds

        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                raise rate_limited()

            timestamps.append(now)


rate_limiter = RateLimiter(max_requests=settings.rate_limit_per_minute)
