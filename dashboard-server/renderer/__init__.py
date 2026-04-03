"""Renderer package — exposes render_dashboard_to_bytes for backward compatibility."""
from config import CONFIG
from config.settings import ScreenConfig
from config.ink import InkDisplayConfig
from .browser import DashboardRenderer


def _make_renderer() -> DashboardRenderer:
    dash = CONFIG.get("dashboard", {})
    screen_cfg = ScreenConfig(
        width=int(dash.get("screen", {}).get("width", 800)),
        height=int(dash.get("screen", {}).get("height", 600)),
    )
    ink_cfg = InkDisplayConfig()
    timeout = int(dash.get("renderer", {}).get("render_timeout", 60000))
    return DashboardRenderer(screen_cfg, ink_cfg, timeout)


_renderer: DashboardRenderer | None = None


def render_dashboard_to_bytes(url, design_width=None, design_height=None):
    """Full pipeline: capture + process. Args ignored (kept for compatibility)."""
    global _renderer
    if _renderer is None:
        _renderer = _make_renderer()
    return _renderer.capture_and_process(url)
