import requests
import html
import re
import time
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from .base import SimpleCache, ServiceProtocol


def _strip_tags(raw_html: str) -> str:
    if not raw_html:
        return ""
    return re.sub(r"<[^>]+>", "", html.unescape(raw_html).strip())


class HackerNewsService:
    def __init__(self, external_url: str, cache: SimpleCache):
        self._external_url = external_url
        self._cache = cache

    @property
    def cache_ttl(self) -> int:
        return self._cache._ttl

    def fetch(self, limit: int = 5) -> list[dict]:
        cache_key = f"hn_{self._external_url}_{limit}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        if self._external_url:
            result = self._fetch_external(limit)
            self._cache.set(cache_key, result)
            return result
        return self._fetch_hn(limit)

    def _fetch_external(self, limit: int) -> list[dict]:
        try:
            resp = requests.get(self._external_url, timeout=10)
            if not resp.ok:
                return []
            items = resp.json()
            return [
                {"title": item.get("title", ""), "meta": item.get("meta", ""), "is_external": True}
                for item in items[:limit]
            ]
        except Exception as e:
            print(f"External News Error: {e}")
            return []

    def _fetch_hn(self, limit: int) -> list[dict]:
        try:
            top_resp = requests.get("https://hacker-news.firebaseio.com/v0/topstories.json", timeout=5)
            best_resp = requests.get("https://hacker-news.firebaseio.com/v0/beststories.json", timeout=5)
            if not top_resp.ok or not best_resp.ok:
                return []

            top_ids = top_resp.json()[:max(limit * 2, 10)]
            best_ids = best_resp.json()[:max(limit * 2, 10)]
            all_ids = list(set(top_ids + best_ids))

            def _fetch_item(sid):
                try:
                    return requests.get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5).json()
                except Exception:
                    return None

            items_map = {}
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_sid = {executor.submit(_fetch_item, sid): sid for sid in all_ids}
                for future in as_completed(future_to_sid):
                    item = future.result()
                    if item and not item.get("deleted") and not item.get("dead"):
                        items_map[item["id"]] = item

            breaking_candidates = []
            now_ts = time.time()

            for sid in top_ids:
                item = items_map.get(sid)
                if not item:
                    continue
                score = item.get("score", 0)
                descendants = item.get("descendants", 0)
                title = item.get("title", "")
                item_time = item.get("time", now_ts)
                age_hours = (now_ts - item_time) / 3600
                if age_hours > 12 or score < 50:
                    continue
                impact = score + (descendants * 0.2)
                sem_mod = 1.0
                title_lower = title.lower()
                subjective = [" i ", " me ", " my ", " how i ", " why i ", "forced me"]
                if any(w in title_lower for w in subjective):
                    sem_mod *= 0.4
                event_words = ["release", "launch", "announce", "available", "open source",
                              "v1.", "v2.", "v3.", "v4.", "gpt", "claude", "llama", "deepseek",
                              "cve-", "zero-day", "hack", "outage"]
                if any(w in title_lower for w in event_words):
                    sem_mod *= 1.5
                velocity = (impact * sem_mod) / math.pow(age_hours + 1.5, 1.8)
                item["velocity"] = velocity
                breaking_candidates.append(item)

            breaking_candidates.sort(key=lambda x: x["velocity"], reverse=True)

            final_list = []
            seen_ids = set()
            if breaking_candidates and breaking_candidates[0]["velocity"] > 30:
                breaker = breaking_candidates[0]
                breaker["is_breaking"] = True
                final_list.append(breaker)
                seen_ids.add(breaker["id"])

            best_candidates = [items_map[sid] for sid in best_ids if sid in items_map]
            for item in best_candidates:
                if len(final_list) >= limit:
                    break
                if item["id"] not in seen_ids:
                    item["is_breaking"] = False
                    final_list.append(item)
                    seen_ids.add(item["id"])

            return [
                {
                    "title": item.get("title"),
                    "score": item.get("score"),
                    "url": item.get("url", ""),
                    "id": item.get("id"),
                    "velocity": item.get("velocity", 0),
                    "time": item.get("time"),
                    "is_breaking": item.get("is_breaking", False),
                    "is_external": False,
                }
                for item in final_list
            ]
        except Exception as e:
            print(f"HN Error: {e}")
            return []


class GitHubTrendingService:
    def __init__(self, cache: SimpleCache):
        self._cache = cache

    @property
    def cache_ttl(self) -> int:
        return self._cache._ttl

    def fetch(self, limit: int = 5) -> list[dict]:
        cache_key = f"gh_trending_{limit}"
        cached = self._cache.get(cache_key)
        if cached:
            return cached

        try:
            resp = requests.get(
                "https://github.com/trending",
                params={"since": "daily"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=10,
            )
            if not resp.ok:
                return []

            items = []
            articles = re.findall(
                r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>',
                resp.text, re.S,
            )
            for block in articles:
                link_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"', block, re.S)
                if not link_match:
                    continue
                repo_path = link_match.group(1).strip()
                repo_name = repo_path.strip("/")
                desc_match = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', block, re.S)
                description = _strip_tags(desc_match.group(1)) if desc_match else ""
                stars_match = re.search(r'href="[^"]+/stargazers"[^>]*>\s*([0-9,]+)\s*<', block)
                stars = stars_match.group(1).strip() if stars_match else ""
                today_match = re.search(r'([0-9,]+)\s+stars\s+today', block)
                stars_today = today_match.group(1).strip() if today_match else ""
                items.append({
                    "name": repo_name,
                    "url": f"https://github.com{repo_path}",
                    "description": description,
                    "stars": stars,
                    "stars_today": stars_today,
                })
                if len(items) >= limit:
                    break

            self._cache.set(cache_key, items)
            return items
        except Exception as e:
            print(f"GitHub Trending Error: {e}")
            return []
