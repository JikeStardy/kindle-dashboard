import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class PageItem:
    id: str
    name: str
    refresh_interval: int
    data_sources: list[str]
    # raw page dict kept for template rendering compatibility
    raw: dict


class PageRepository:
    _pages: dict = {}

    @classmethod
    def load(cls, pages_default: dict, pages_default_path: str):
        if isinstance(pages_default, dict) and pages_default:
            cls._pages = pages_default
            return

        path = Path(pages_default_path)
        if not pages_default_path:
            cls._pages = {}
            return
        if not path.is_absolute():
            path = Path(__file__).parent.parent / path
        if not path.exists():
            cls._pages = {}
            return

        try:
            if path.suffix.lower() in {".yaml", ".yml"}:
                import yaml
                with path.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            else:
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
        except Exception:
            cls._pages = {}
            return

        cls._pages = data if isinstance(data, dict) else {}

    @classmethod
    def get_all(cls) -> dict:
        return cls._pages

    @classmethod
    def get(cls, page_id: str) -> Optional[PageItem]:
        pages = cls._pages
        if page_id in pages:
            return cls._make_item(page_id, pages[page_id])
        return None

    @classmethod
    def _make_item(cls, page_id: str, raw: dict) -> PageItem:
        cells = raw.get("cells", [])
        data_sources = []
        for cell in cells:
            comp = cell.get("component", "")
            if comp not in data_sources:
                data_sources.append(comp)
        return PageItem(
            id=page_id,
            name=raw.get("name", page_id),
            refresh_interval=raw.get("refresh_interval", 0),
            data_sources=data_sources,
            raw=raw,
        )
