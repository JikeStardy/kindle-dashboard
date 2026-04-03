from dataclasses import dataclass


@dataclass
class InkDisplayConfig:
    colors: int = 16
    dither: bool = False
    format: str = "png"
