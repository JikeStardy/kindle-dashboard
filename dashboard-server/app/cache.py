import threading
import time
from renderer.browser import DashboardRenderer


class RenderCache:
    def __init__(self, renderer: DashboardRenderer, ttl: int):
        self._renderer = renderer
        self._ttl = ttl
        self._cache: dict[str, tuple[bytes, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> tuple[bytes, float] | None:
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            data, timestamp = entry
            if time.time() - timestamp < self._ttl:
                return entry
            del self._cache[key]
            return None

    def set(self, key: str, data: bytes):
        with self._lock:
            self._cache[key] = (data, time.time())

    def get_page_ids(self) -> list[str]:
        with self._lock:
            return list(self._cache.keys())
