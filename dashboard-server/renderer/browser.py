import threading
import datetime
from playwright.sync_api import sync_playwright
from config.settings import ScreenConfig
from config.ink import InkDisplayConfig
from .processing import ImageProcessor


_thread_state = threading.local()
_browser_lock = threading.Lock()


class DashboardRenderer:
    def __init__(self, screen: ScreenConfig, ink: InkDisplayConfig, render_timeout: int):
        self._screen = screen
        self._ink = ink
        self._timeout = render_timeout
        self._processor = ImageProcessor(ink)

    def capture(self, url: str) -> bytes:
        with _browser_lock:
            if not hasattr(_thread_state, "browser") or _thread_state.browser is None:
                _thread_state.playwright = sync_playwright().start()
                _thread_state.browser = _thread_state.playwright.chromium.launch(headless=True)
            browser = _thread_state.browser

        page = browser.new_page(
            viewport={"width": self._screen.width, "height": self._screen.height},
            device_scale_factor=1,
        )
        reset_needed = False
        try:
            page.goto(url, wait_until="networkidle", timeout=self._timeout)
            screenshot_bytes = page.screenshot(type="png")
            return screenshot_bytes
        except Exception as e:
            print(f"Error capturing screenshot: {e}")
            reset_needed = True
            raise
        finally:
            try:
                page.close()
            except Exception as e:
                print(f"Error closing page: {e}")
            if reset_needed:
                self._reset_browser()

    def _reset_browser(self):
        with _browser_lock:
            if hasattr(_thread_state, "browser") and _thread_state.browser is not None:
                try:
                    _thread_state.browser.close()
                except Exception:
                    pass
            if hasattr(_thread_state, "playwright") and _thread_state.playwright is not None:
                try:
                    _thread_state.playwright.stop()
                except Exception:
                    pass
            _thread_state.browser = None
            _thread_state.playwright = None

    def process(self, input_bytes: bytes) -> bytes:
        return self._processor.process(input_bytes).getvalue()

    def capture_and_process(self, url: str) -> bytes:
        start = datetime.datetime.now()
        print(f"[{start}] Starting Render Job for {url}")
        raw = self.capture(url)
        processed = self.process(raw)
        end = datetime.datetime.now()
        print(f"[{end}] Render finished in {(end - start).total_seconds()}s")
        return processed

    def close(self):
        self._reset_browser()
