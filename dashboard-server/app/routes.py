import datetime
import hashlib
import io
import time
from flask import Flask, render_template, send_file, jsonify, request
from config import AppConfig
from config.pages import PageRepository
from renderer import render_dashboard_to_bytes
from .dashboard import fetch_dashboard_data
from .cache import RenderCache
from .workers import BackgroundTaskScheduler, FailureTracker
from services import ServiceRegistry


def _grid_fr(values):
    return " ".join(f"{v}fr" for v in values)


def register_routes(
    app: Flask,
    cfg: AppConfig,
    render_cache: RenderCache,
    scheduler: BackgroundTaskScheduler,
    failure_tracker: FailureTracker,
    registry: ServiceRegistry,
):
    @app.route("/")
    @app.route("/health")
    def health():
        return "OK"

    @app.route("/dashboard")
    @app.route("/dashboard/<page_id>")
    def render_page(page_id=None):
        resolved_id, page = _get_page(page_id or cfg.default_page, cfg.default_page)
        font_scale = request.args.get("font_scale")
        if font_scale:
            page = _apply_font_scale(page, font_scale)
        grid = page.get("grid", {})
        return render_template(
            "dashboard_dynamic.html",
            page_id=resolved_id,
            page=page,
            grid_cols=_grid_fr(grid.get("columns", [1, 1])),
            grid_rows=_grid_fr(grid.get("rows", [1, 1])),
            config=_LegacyConfigShim(cfg),
        )

    @app.route("/api/data")
    def dashboard_data():
        page_id = request.args.get("page", cfg.default_page)
        return jsonify(fetch_dashboard_data(
            page_id, registry, cfg.clock_format, cfg.location.timezone, cfg.language
        ))

    @app.route("/api/settings")
    def settings():
        result = {}
        for key in dir(_LegacyConfigShim):
            val = getattr(_LegacyConfigShim, key, None)
            if key.isupper() and not callable(val):
                result[key] = val
        result["_computed"] = {
            "pages": PageRepository.get_all(),
            "finance_tickers": cfg.finance_tickers,
        }
        return jsonify(result)

    @app.route("/api/ink_setting")
    def ink_setting():
        return jsonify({
            "img_url": cfg.ink_img_url,
            "interval": cfg.ink_interval,
            "full_refresh_cycle": cfg.ink_full_refresh_cycle,
            "base_dir": cfg.ink_base_dir,
            "tmp_file": cfg.ink_tmp_file,
            "log_file": cfg.ink_log_file,
            "safety_lock": cfg.ink_safety_lock,
            "ping_target": cfg.ink_ping_target,
            "rotate": cfg.ink_rotate,
            "enable_local_clock": cfg.ink_enable_local_clock,
            "clock_x": cfg.ink_clock_x,
            "clock_y": cfg.ink_clock_y,
            "clock_size": cfg.ink_clock_size,
            "clock_font": cfg.ink_clock_font,
            "time_format": cfg.ink_time_format,
            "max_fail_count": cfg.ink_max_fail_count,
            "wifi_interface": cfg.ink_wifi_interface,
            "settings_path": cfg.ink_settings_path,
        })

    @app.route("/render")
    @app.route("/render.png")
    def render_dashboard():
        page_id = request.args.get("page", cfg.default_page)
        font_scale = request.args.get("font_scale")
        _, page = _get_page(page_id, cfg.default_page)
        if font_scale:
            page = _apply_font_scale(page, font_scale)
        cache_key = page_id

        current_time = time.time()
        cached = render_cache.get(cache_key)

        if cached:
            data, timestamp = cached
            failure_tracker.record_success()
            return _make_response(data, timestamp, cfg.cache.render_seconds)

        if cached is None:
            try:
                design = page.get("design", {}) if isinstance(page, dict) else {}
                url = f"http://127.0.0.1:{cfg.server.port}/dashboard/{page_id}"
                if font_scale:
                    url += f"?font_scale={font_scale}"
                image_bytes = render_dashboard_to_bytes(
                    url,
                    design_width=design.get("width"),
                    design_height=design.get("height"),
                )
                render_cache.set(cache_key, image_bytes)
                failure_tracker.record_success()
                return _make_response(image_bytes, current_time, cfg.cache.render_seconds)
            except Exception as e:
                import traceback
                traceback.print_exc()
                failure_tracker.record_failure()
                return f"Error rendering dashboard: {e}", 500

        return _make_response(cached[0], cached[1], cfg.cache.render_seconds)


def _get_page(page_id, default_page):
    pages = PageRepository.get_all()
    if page_id in pages:
        return page_id, pages[page_id]
    if default_page in pages:
        return default_page, pages[default_page]
    return page_id, next(iter(pages.values()))


def _apply_font_scale(page, font_scale):
    try:
        scale = float(font_scale)
    except (TypeError, ValueError):
        return page
    page = dict(page)
    theme = dict(page.get("theme", {}))
    theme["font_scale"] = scale
    page["theme"] = theme
    return page


def _make_response(data: bytes, timestamp: float, cache_ttl: int):
    response = send_file(
        io.BytesIO(data),
        mimetype="image/png",
        as_attachment=False,
        download_name="dashboard.png",
    )
    response.headers["Cache-Control"] = f"public, max-age={cache_ttl}, s-maxage={cache_ttl}"
    last_modified = datetime.datetime.fromtimestamp(timestamp, datetime.UTC)
    response.headers["Last-Modified"] = last_modified.strftime("%a, %d %b %Y %H:%M:%S GMT")
    response.set_etag(hashlib.md5(data).hexdigest())
    return response


class _LegacyConfigShim:
    """Provides Config-like access for templates during transition."""
    def __init__(self, cfg: AppConfig):
        self._cfg = cfg

    def __getattr__(self, name: str):
        mapping = {
            "PORT": self._cfg.server.port,
            "HOST": self._cfg.server.host,
            "SCREEN_WIDTH": self._cfg.screen.width,
            "SCREEN_HEIGHT": self._cfg.screen.height,
            "LATITUDE": self._cfg.location.latitude,
            "LONGITUDE": self._cfg.location.longitude,
            "CITY_NAME": self._cfg.location.city_name,
            "TIMEZONE": self._cfg.location.timezone,
            "LANGUAGE": self._cfg.language,
            "CLOCK_FORMAT": self._cfg.clock_format,
            "RENDER_TIMEOUT": self._cfg.render_timeout,
            "DEFAULT_PAGE": self._cfg.default_page,
        }
        if name in mapping:
            return mapping[name]
        raise AttributeError(f"no attribute {name}")
