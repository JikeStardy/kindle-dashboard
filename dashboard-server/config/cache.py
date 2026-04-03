from dataclasses import dataclass


@dataclass
class CacheTTLConfig:
    weather_seconds: int = 600
    finance_seconds: int = 900
    news_seconds: int = 300
    render_seconds: int = 60
