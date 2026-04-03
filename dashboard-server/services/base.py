import threading
import time
from typing import Protocol


class SimpleCache:
    def __init__(self, ttl_seconds: int):
        self._ttl = ttl_seconds
        self._data: dict = {}
        self._timestamps: dict = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            item = self._data.get(key)
            if item:
                val, timestamp = item
                if time.time() - timestamp < self._ttl:
                    return val
                else:
                    del self._data[key]
                    if key in self._timestamps:
                        del self._timestamps[key]
        return None

    def set(self, key: str, value):
        with self._lock:
            self._data[key] = (value, time.time())


class ServiceProtocol(Protocol):
    def fetch(self) -> dict:
        ...

    @property
    def cache_ttl(self) -> int:
        ...
