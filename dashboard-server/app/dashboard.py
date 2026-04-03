import datetime
from zoneinfo import ZoneInfo
from config.pages import PageRepository
from services import ServiceRegistry


def fetch_dashboard_data(page_id: str, registry: ServiceRegistry,
                          clock_format: str, timezone: str, language: str) -> dict:
    pages = PageRepository.get_all() or {}
    resolved = page_id
    if page_id not in pages:
        from config import Config
        resolved = Config.DEFAULT_PAGE
    raw_page = pages.get(resolved) or pages.get(next(iter(pages.keys()), {}))

    cells = raw_page.get("cells", []) if isinstance(raw_page, dict) else []
    news_limit = _component_limit(cells, "news", default=5)
    github_limit = _component_limit(cells, "github_trending", default=5)

    sources = ["weather", "calendar", "hackernews", "github_trending"]
    results = registry.get_multi(sources)

    weather = results.get("weather", {"current": {"temp": "--"}, "forecast": [], "tomorrow": {}})
    calendar = results.get("calendar", {"date_str": "--", "weekday": "--", "lunar": "--"})
    news = results.get("hackernews", [])
    github_trending = results.get("github_trending", [])

    now_local = datetime.datetime.now(ZoneInfo(timezone))
    now_local += datetime.timedelta(seconds=60)
    updated_at = now_local.strftime("%H:%M")
    clock_time = now_local.strftime(clock_format)

    return {
        "weather": weather,
        "calendar": calendar,
        "news": news,
        "github_trending": github_trending,
        "finance": [],
        "clock": {"time": clock_time},
        "meta": {"updated_at": updated_at, "language": language},
    }


def _component_limit(cells: list, component: str, default: int = 5) -> int:
    limits = []
    for cell in cells:
        if cell.get("component") != component:
            continue
        limit = cell.get("options", {}).get("limit")
        if isinstance(limit, int) and limit > 0:
            limits.append(limit)
    return max(limits) if limits else default
