from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .base import SimpleCache, ServiceProtocol
from .weather import WeatherService
from .calendar import CalendarService
from .news import HackerNewsService, GitHubTrendingService
from .finance import FinanceService


class ServiceRegistry:
    def __init__(self):
        self._services: dict[str, ServiceProtocol] = {}

    def register(self, name: str, service: ServiceProtocol):
        self._services[name] = service

    def get(self, name: str) -> ServiceProtocol:
        return self._services[name]

    def get_multi(self, names: list[str]) -> dict[str, dict]:
        results = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {
                name: executor.submit(self._services[name].fetch)
                for name in names
                if name in self._services
            }
            for name, future in futures.items():
                try:
                    results[name] = future.result(timeout=15)
                except Exception as e:
                    print(f"Service {name} failed: {e}")
                    results[name] = {}
        return results


def build_registry(
    weather_cache: SimpleCache,
    finance_cache: SimpleCache,
    news_cache: SimpleCache,
    github_cache: SimpleCache,
    latitude: float,
    longitude: float,
    timezone: str,
    language: str,
    holiday_country: str,
    work_start: int,
    work_end: int,
    news_external_url: str,
    finance_tickers: list[dict],
) -> ServiceRegistry:
    registry = ServiceRegistry()
    registry.register("weather", WeatherService(
        latitude, longitude, timezone, language, work_start, work_end, weather_cache
    ))
    registry.register("calendar", CalendarService(
        timezone, language, holiday_country, weather_cache
    ))
    registry.register("hackernews", HackerNewsService(news_external_url, news_cache))
    registry.register("github_trending", GitHubTrendingService(github_cache))
    registry.register("finance", FinanceService(finance_tickers, finance_cache))
    return registry
