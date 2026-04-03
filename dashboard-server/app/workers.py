import os
import signal
import threading
import time
from config.pages import PageRepository


class FailureTracker:
    def __init__(self, threshold: int):
        self._count = 0
        self._threshold = threshold

    def record_failure(self):
        self._count += 1
        if self._count >= self._threshold:
            self._restart()

    def record_success(self):
        self._count = 0

    def _restart(self):
        print("CRITICAL: Too many consecutive rendering errors. Restarting container...")
        try:
            os.kill(1, signal.SIGTERM)
        except PermissionError:
            print("Could not kill PID 1 (Permission Denied). Killing self instead.")
            os.kill(os.getpid(), signal.SIGTERM)


class BackgroundTaskScheduler:
    def __init__(self, render_cache, port: int, render_func):
        self._render_cache = render_cache
        self._port = port
        self._render_func = render_func
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self):
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self._thread.start()

    def stop(self):
        with self._lock:
            self._running = False
            if self._thread:
                self._thread.join(timeout=5)

    def _refresh_loop(self):
        while self._running:
            now = time.time()
            next_minute = (int(now) // 60 + 1) * 60
            delay = max(0, (next_minute + 30) - now)
            time.sleep(delay)
            if not self._running:
                break
            try:
                pages = PageRepository.get_all() or {}
                for page_id in pages.keys():
                    url = f"http://127.0.0.1:{self._port}/dashboard/{page_id}"
                    data = self._render_func(url)
                    self._render_cache.set(page_id, data)
            except Exception as e:
                print(f"[Cache] Background refresh failed: {e}")
