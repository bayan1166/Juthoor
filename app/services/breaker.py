import time
from threading import Lock


class Breaker:
    def __init__(self, threshold=2, cooldown=60.0, clock=time.monotonic):
        self.threshold = threshold
        self.cooldown = cooldown
        self._clock = clock
        self._failures = 0
        self._open_until = 0.0
        self._lock = Lock()

    def allow(self):
        with self._lock:
            if self._clock() >= self._open_until:
                return True
            return False

    def success(self):
        with self._lock:
            self._failures = 0
            self._open_until = 0.0

    def failure(self):
        with self._lock:
            self._failures += 1
            if self._failures >= self.threshold:
                self._open_until = self._clock() + self.cooldown
                self._failures = 0

    def is_open(self):
        return not self.allow()
