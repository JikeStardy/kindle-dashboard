from pathlib import Path
import yaml
from dataclasses import dataclass, fields

from .settings import ServerConfig, ScreenConfig, LocationConfig
from .ink import InkDisplayConfig
from .cache import CacheTTLConfig
from .pages import PageItem, PageRepository


CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

DEFAULT_CONFIG = {
    "dashboard": {
        "server": {"port": 15000, "host": "0.0.0.0"},
        "location": {
            "latitude": 22.52935041976462,
            "longitude": 113.94669211479524,
            "city_name": "Shenzhen",
            "timezone": "Asia/Shanghai",
            "locale": "CN",
        },
        "screen": {"width": 800, "height": 600},
        "pages": {
            "default_page": "default",
            "pages_default_path": "pages_default.json",
            "pages": {},
        },
        "renderer": {"render_timeout": 60000},
        "locale": {"language": "CN", "holiday_country": "CN"},
        "clock": {"clock_format": "%H:%M"},
        "cache_ttl": {"weather": 600, "finance": 900, "news": 300, "render": 60},
        "work": {"start_hour": 10, "end_hour": 18},
        "news": {"external_url": ""},
        "finance": {
            "tickers": [
                {"symbol": "SGDCNY=X", "name": "SGD/CNY"},
                {"symbol": "CNY=X", "name": "USD/CNY"},
                {"symbol": "BTC-USD", "name": "BTC/USD"},
            ]
        },
    },
    "ink_setting": {
        "img_url": "http://127.0.0.1:5000/render",
        "interval": 300,
        "full_refresh_cycle": 12,
        "base_dir": "/mnt/us/extensions/Kindle-Dashboard",
        "tmp_file": "/tmp/dashboard_download.png",
        "log_file": "/tmp/dashboard.log",
        "safety_lock": "/mnt/us/STOP_DASH",
        "ping_target": "223.5.5.5",
        "rotate": 3,
        "enable_local_clock": 1,
        "clock_x": 40,
        "clock_y": 295,
        "clock_size": 80,
        "clock_font": "/mnt/us/extensions/Kindle-Dashboard/IBMPlexMono-SemiBold.ttf",
        "time_format": 12,
        "max_fail_count": 6,
        "wifi_interface": "wlan0",
        "settings_path": "/api/ink_setting",
    },
}


def _merge_dict(base, override):
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    merged = dict(base)
    for key, value in override.items():
        if key in merged:
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(config_path: str | None = None) -> dict:
    """Load and merge config from YAML file."""
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        raw = {}
    else:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    return _merge_dict(DEFAULT_CONFIG, raw)


# Module-level raw config dict (kept for compatibility)
CONFIG = load_config()
DASHBOARD_CONFIG = CONFIG.get("dashboard", {})
INK_SETTING = CONFIG.get("ink_setting", {})


@dataclass
class AppConfig:
    """Aggregated config object passed to app factory."""
    server: ServerConfig
    screen: ScreenConfig
    location: LocationConfig
    cache: CacheTTLConfig
    ink: InkDisplayConfig
    pages_default: dict
    pages_default_path: str
    default_page: str
    render_timeout: int
    language: str
    holiday_country: str
    clock_format: str
    work_start_hour: int
    work_end_hour: int
    news_external_url: str
    finance_tickers: list[dict]
    # ink settings
    ink_img_url: str
    ink_interval: int
    ink_full_refresh_cycle: int
    ink_base_dir: str
    ink_tmp_file: str
    ink_log_file: str
    ink_safety_lock: str
    ink_ping_target: str
    ink_rotate: int
    ink_enable_local_clock: int
    ink_clock_x: int
    ink_clock_y: int
    ink_clock_size: int
    ink_clock_font: str
    ink_time_format: int
    ink_max_fail_count: int
    ink_wifi_interface: str
    ink_settings_path: str

    @classmethod
    def from_dict(cls, cfg: dict) -> "AppConfig":
        dash = cfg.get("dashboard", {})
        ink = cfg.get("ink_setting", {})
        loc = dash.get("location", {})
        srv = dash.get("server", {})
        screen = dash.get("screen", {})
        cache = dash.get("cache_ttl", {})
        finance = dash.get("finance", {})
        return cls(
            server=ServerConfig(
                host=srv.get("host", "0.0.0.0"),
                port=int(srv.get("port", 15000)),
            ),
            screen=ScreenConfig(
                width=int(screen.get("width", 800)),
                height=int(screen.get("height", 600)),
            ),
            location=LocationConfig(
                latitude=float(loc.get("latitude", 0.0)),
                longitude=float(loc.get("longitude", 0.0)),
                timezone=loc.get("timezone", "UTC"),
                locale=loc.get("locale", "CN"),
                city_name=loc.get("city_name", ""),
            ),
            cache=CacheTTLConfig(
                weather_seconds=int(cache.get("weather", 600)),
                finance_seconds=int(cache.get("finance", 900)),
                news_seconds=int(cache.get("news", 300)),
                render_seconds=int(cache.get("render", 60)),
            ),
            ink=InkDisplayConfig(),
            pages_default=dash.get("pages", {}).get("pages", {}),
            pages_default_path=dash.get("pages", {}).get("pages_default_path", "pages_default.json"),
            default_page=dash.get("pages", {}).get("default_page", "default"),
            render_timeout=int(dash.get("renderer", {}).get("render_timeout", 60000)),
            language=dash.get("locale", {}).get("language", "CN"),
            holiday_country=dash.get("locale", {}).get("holiday_country", "CN"),
            clock_format=dash.get("clock", {}).get("clock_format", "%H:%M"),
            work_start_hour=int(dash.get("work", {}).get("start_hour", 10)),
            work_end_hour=int(dash.get("work", {}).get("end_hour", 18)),
            news_external_url=dash.get("news", {}).get("external_url", ""),
            finance_tickers=finance.get("tickers", []),
            ink_img_url=ink.get("img_url", ""),
            ink_interval=int(ink.get("interval", 300)),
            ink_full_refresh_cycle=int(ink.get("full_refresh_cycle", 12)),
            ink_base_dir=ink.get("base_dir", "/mnt/us/extensions/Kindle-Dashboard"),
            ink_tmp_file=ink.get("tmp_file", "/tmp/dashboard_download.png"),
            ink_log_file=ink.get("log_file", "/tmp/dashboard.log"),
            ink_safety_lock=ink.get("safety_lock", "/mnt/us/STOP_DASH"),
            ink_ping_target=ink.get("ping_target", "223.5.5.5"),
            ink_rotate=int(ink.get("rotate", 3)),
            ink_enable_local_clock=int(ink.get("enable_local_clock", 1)),
            ink_clock_x=int(ink.get("clock_x", 40)),
            ink_clock_y=int(ink.get("clock_y", 295)),
            ink_clock_size=int(ink.get("clock_size", 80)),
            ink_clock_font=ink.get("clock_font", "/mnt/us/extensions/Kindle-Dashboard/IBMPlexMono-SemiBold.ttf"),
            ink_time_format=int(ink.get("time_format", 12)),
            ink_max_fail_count=int(ink.get("max_fail_count", 6)),
            ink_wifi_interface=ink.get("wifi_interface", "wlan0"),
            ink_settings_path=ink.get("settings_path", "/api/ink_setting"),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Lazy class attribute descriptor
# ─────────────────────────────────────────────────────────────────────────────

class _LazyAttr:
    """Descriptor that calls a getter on the class and caches the result."""
    def __init__(self, getter):
        self.getter = getter
        self.cache_key = None

    def __get__(self, obj, objtype=None):
        if self.cache_key is None:
            self.cache_key = f"_lazy_{id(self)}"
        cached = objtype.__dict__.get(self.cache_key) if objtype else None
        if cached is not None:
            return cached
        value = self.getter(objtype)
        objtype.__dict__[self.cache_key] = value
        return value


# ─────────────────────────────────────────────────────────────────────────────
# Legacy Config class — backward compatibility wrapper
# ─────────────────────────────────────────────────────────────────────────────

class Config:
    """Compatibility shim. Delegates to AppConfig fields."""

    _cfg: AppConfig = None

    @classmethod
    def _ensure(cls) -> AppConfig:
        if cls._cfg is None:
            cls._cfg = AppConfig.from_dict(CONFIG)
            PageRepository.load(cls._cfg.pages_default, cls._cfg.pages_default_path)
        return cls._cfg

    # Server
    PORT = _LazyAttr(lambda cls: cls._ensure().server.port)
    HOST = _LazyAttr(lambda cls: cls._ensure().server.host)

    # Location
    LATITUDE = _LazyAttr(lambda cls: cls._ensure().location.latitude)
    LONGITUDE = _LazyAttr(lambda cls: cls._ensure().location.longitude)
    CITY_NAME = _LazyAttr(lambda cls: cls._ensure().location.city_name)
    TIMEZONE = _LazyAttr(lambda cls: cls._ensure().location.timezone)

    # Screen
    SCREEN_WIDTH = _LazyAttr(lambda cls: cls._ensure().screen.width)
    SCREEN_HEIGHT = _LazyAttr(lambda cls: cls._ensure().screen.height)

    # Pages
    DEFAULT_PAGE = _LazyAttr(lambda cls: cls._ensure().default_page)
    PAGES_DEFAULT_PATH = _LazyAttr(lambda cls: cls._ensure().pages_default_path)
    PAGES_DEFAULT = _LazyAttr(lambda cls: cls._ensure().pages_default)

    # Renderer
    RENDER_TIMEOUT = _LazyAttr(lambda cls: cls._ensure().render_timeout)

    # Locale
    LANGUAGE = _LazyAttr(lambda cls: cls._ensure().language)
    HOLIDAY_COUNTRY = _LazyAttr(lambda cls: cls._ensure().holiday_country)

    # Clock
    CLOCK_FORMAT = _LazyAttr(lambda cls: cls._ensure().clock_format)

    # Cache TTL
    CACHE_TTL_WEATHER = _LazyAttr(lambda cls: cls._ensure().cache.weather_seconds)
    CACHE_TTL_FINANCE = _LazyAttr(lambda cls: cls._ensure().cache.finance_seconds)
    CACHE_TTL_NEWS = _LazyAttr(lambda cls: cls._ensure().cache.news_seconds)
    CACHE_TTL_RENDER = _LazyAttr(lambda cls: cls._ensure().cache.render_seconds)

    # Work hours
    WORK_START_HOUR = _LazyAttr(lambda cls: cls._ensure().work_start_hour)
    WORK_END_HOUR = _LazyAttr(lambda cls: cls._ensure().work_end_hour)

    # News
    NEWS_EXTERNAL_URL = _LazyAttr(lambda cls: cls._ensure().news_external_url)

    # Finance
    FINANCE_TICKERS = _LazyAttr(lambda cls: cls._ensure().finance_tickers)

    # Ink settings
    INK_IMG_URL = _LazyAttr(lambda cls: cls._ensure().ink_img_url)
    INK_INTERVAL = _LazyAttr(lambda cls: cls._ensure().ink_interval)
    INK_FULL_REFRESH_CYCLE = _LazyAttr(lambda cls: cls._ensure().ink_full_refresh_cycle)
    INK_BASE_DIR = _LazyAttr(lambda cls: cls._ensure().ink_base_dir)
    INK_TMP_FILE = _LazyAttr(lambda cls: cls._ensure().ink_tmp_file)
    INK_LOG_FILE = _LazyAttr(lambda cls: cls._ensure().ink_log_file)
    INK_SAFETY_LOCK = _LazyAttr(lambda cls: cls._ensure().ink_safety_lock)
    INK_PING_TARGET = _LazyAttr(lambda cls: cls._ensure().ink_ping_target)
    INK_ROTATE = _LazyAttr(lambda cls: cls._ensure().ink_rotate)
    INK_ENABLE_LOCAL_CLOCK = _LazyAttr(lambda cls: cls._ensure().ink_enable_local_clock)
    INK_CLOCK_X = _LazyAttr(lambda cls: cls._ensure().ink_clock_x)
    INK_CLOCK_Y = _LazyAttr(lambda cls: cls._ensure().ink_clock_y)
    INK_CLOCK_SIZE = _LazyAttr(lambda cls: cls._ensure().ink_clock_size)
    INK_CLOCK_FONT = _LazyAttr(lambda cls: cls._ensure().ink_clock_font)
    INK_TIME_FORMAT = _LazyAttr(lambda cls: cls._ensure().ink_time_format)
    INK_MAX_FAIL_COUNT = _LazyAttr(lambda cls: cls._ensure().ink_max_fail_count)
    INK_WIFI_INTERFACE = _LazyAttr(lambda cls: cls._ensure().ink_wifi_interface)
    INK_SETTINGS_PATH = _LazyAttr(lambda cls: cls._ensure().ink_settings_path)

    @staticmethod
    def get_finance_tickers():
        tickers = Config.FINANCE_TICKERS
        if isinstance(tickers, dict):
            tickers = [tickers]
        if isinstance(tickers, str):
            return [{"symbol": tickers.strip(), "name": tickers.strip()}] if tickers.strip() else []
        if not isinstance(tickers, list):
            return []
        normalized = []
        for item in tickers:
            if isinstance(item, dict):
                symbol = str(item.get("symbol", "")).strip()
                if not symbol:
                    continue
                name = str(item.get("name", symbol)).strip() or symbol
                normalized.append({"symbol": symbol, "name": name})
            elif isinstance(item, str):
                symbol = item.strip()
                if symbol:
                    normalized.append({"symbol": symbol, "name": symbol})
        return normalized

    @staticmethod
    def get_pages():
        cfg = Config._ensure()
        if isinstance(cfg.pages_default, dict) and cfg.pages_default:
            return cfg.pages_default
        PageRepository.load(cfg.pages_default, cfg.pages_default_path)
        return PageRepository.get_all()

    @staticmethod
    def get_page(page_id=None):
        pages = Config.get_pages()
        pid = page_id or Config.DEFAULT_PAGE
        if pid in pages:
            return pages[pid]
        if Config.DEFAULT_PAGE in pages:
            return pages[Config.DEFAULT_PAGE]
        return next(iter(pages.values()))
