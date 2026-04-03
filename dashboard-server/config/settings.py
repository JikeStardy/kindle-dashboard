from dataclasses import dataclass


@dataclass
class ServerConfig:
    host: str
    port: int
    debug: bool = False


@dataclass
class ScreenConfig:
    width: int      # default 800
    height: int    # default 600


@dataclass
class LocationConfig:
    latitude: float
    longitude: float
    timezone: str    # e.g. "Asia/Shanghai"
    locale: str      # e.g. "CN"
    city_name: str
