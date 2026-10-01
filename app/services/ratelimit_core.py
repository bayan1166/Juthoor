import time
from collections import defaultdict, deque
from threading import Lock


class SlidingWindow:
    def __init__(self, clock=time.monotonic):
        self._clock = clock
        self._hits = defaultdict(deque)
        self._windows = {}
        self._lock = Lock()
        self._ops = 0

    def _trim(self, key, window, now):
        q = self._hits[key]
        cutoff = now - window
        while q and q[0] <= cutoff:
            q.popleft()
        return q

    def _purge(self, now):
        for key in list(self._hits):
            q = self._hits[key]
            if not q or q[-1] <= now - self._windows.get(key, 0):
                del self._hits[key]
                self._windows.pop(key, None)

    def _tick(self, now):
        self._ops += 1
        if self._ops % 2000 == 0:
            self._purge(now)

    def hit(self, key, limit, window):
        now = self._clock()
        with self._lock:
            q = self._trim(key, window, now)
            self._windows[key] = window
            if len(q) >= limit:
                return False, max(1, int(q[0] + window - now) + 1)
            q.append(now)
            self._tick(now)
            return True, 0

    def record(self, key, window):
        now = self._clock()
        with self._lock:
            self._trim(key, window, now)
            self._windows[key] = window
            self._hits[key].append(now)
            self._tick(now)

    def count(self, key, window):
        now = self._clock()
        with self._lock:
            if key not in self._hits:
                return 0
            return len(self._trim(key, window, now))

    def retry_after(self, key, window):
        now = self._clock()
        with self._lock:
            if key not in self._hits:
                return 1
            q = self._trim(key, window, now)
            return max(1, int(q[0] + window - now) + 1) if q else 1

    def clear(self, key):
        with self._lock:
            self._hits.pop(key, None)
            self._windows.pop(key, None)

    def reset(self):
        with self._lock:
            self._hits.clear()
            self._windows.clear()
