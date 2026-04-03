import os
from flask import Flask
from config import CONFIG, AppConfig
from config.settings import ScreenConfig
from config.ink import InkDisplayConfig
from config.pages import PageRepository
from renderer import render_dashboard_to_bytes
from renderer.browser import DashboardRenderer
from services.base import SimpleCache
from services import build_registry
from .routes import register_routes
from .cache import RenderCache
from .workers import BackgroundTaskScheduler, FailureTracker


def create_app(config_path: str | None = None) -> Flask:
    if config_path:
        from config import load_config
        global CONFIG
        CONFIG = load_config(config_path)

    cfg = AppConfig.from_dict(CONFIG)
    PageRepository.load(cfg.pages_default, cfg.pages_default_path)

    # Build services
    weather_cache = SimpleCache(cfg.cache.weather_seconds)
    finance_cache = SimpleCache(cfg.cache.finance_seconds)
    news_cache = SimpleCache(cfg.cache.news_seconds)
    github_cache = SimpleCache(cfg.cache.news_seconds)

    registry = build_registry(
        weather_cache=weather_cache,
        finance_cache=finance_cache,
        news_cache=news_cache,
        github_cache=github_cache,
        latitude=cfg.location.latitude,
        longitude=cfg.location.longitude,
        timezone=cfg.location.timezone,
        language=cfg.language,
        holiday_country=cfg.holiday_country,
        work_start=cfg.work_start_hour,
        work_end=cfg.work_end_hour,
        news_external_url=cfg.news_external_url,
        finance_tickers=cfg.finance_tickers,
    )

    # Build renderer
    screen = ScreenConfig(width=cfg.screen.width, height=cfg.screen.height)
    ink = InkDisplayConfig()
    renderer = DashboardRenderer(screen, ink, cfg.render_timeout)

    # Build render cache
    render_cache = RenderCache(renderer, cfg.cache.render_seconds)

    # Build workers
    failure_tracker = FailureTracker(threshold=5)
    scheduler = BackgroundTaskScheduler(
        render_cache=render_cache,
        port=cfg.server.port,
        render_func=lambda url: render_dashboard_to_bytes(url),
    )

    # Start background refresh
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or os.environ.get("FLASK_DEBUG", "0").lower() in ("0", "false", "no", ""):
        scheduler.start()

    # Create and configure Flask app
    app = Flask(__name__)
    register_routes(app, cfg, render_cache, scheduler, failure_tracker, registry)
    return app
