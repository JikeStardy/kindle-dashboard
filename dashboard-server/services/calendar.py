import datetime
from zoneinfo import ZoneInfo
from lunardate import LunarDate
import holidays
from .base import SimpleCache, ServiceProtocol


WEEKDAYS_CN = {
    "Monday": "星期一", "Tuesday": "星期二", "Wednesday": "星期三",
    "Thursday": "星期四", "Friday": "星期五", "Saturday": "星期六",
    "Sunday": "星期日",
}


class CalendarService:
    def __init__(self, timezone: str, language: str, holiday_country: str, cache: SimpleCache):
        self._tz = timezone
        self._lang = language
        self._country = holiday_country
        self._cache = cache

    @property
    def cache_ttl(self) -> int:
        return self._cache._ttl

    def fetch(self) -> dict:
        cached = self._cache.get("calendar_info")
        if cached:
            return cached

        now = datetime.datetime.now(ZoneInfo(self._tz))
        lunar = LunarDate.fromSolarDate(now.year, now.month, now.day)
        lunar_str = f"Lunar {lunar.month}/{lunar.day}" if self._lang == "EN" else f"农历 {lunar.month}月{lunar.day}日"

        try:
            if hasattr(holidays, self._country):
                country_holidays = getattr(holidays, self._country)(years=now.year)
            else:
                country_holidays = holidays.SG(years=now.year)
        except Exception:
            country_holidays = holidays.SG(years=now.year)

        today_holiday = country_holidays.get(now.date())
        today_is_weekend = now.weekday() >= 5
        is_rest_today = bool(today_holiday) or today_is_weekend

        today_status = None
        if is_rest_today:
            if today_holiday:
                today_status = today_holiday
            else:
                today_status = "星期六" if now.weekday() == 5 else "星期日" if self._lang != "EN" else ("Saturday" if now.weekday() == 5 else "Sunday")

        next_day = None
        next_date = now.date() + datetime.timedelta(days=1)

        if is_rest_today:
            for _ in range(30):
                d_is_weekend = next_date.weekday() >= 5
                d_is_holiday = country_holidays.get(next_date)
                if not d_is_weekend and not d_is_holiday:
                    weekday_en = next_date.strftime("%A")
                    label = weekday_en if self._lang == "EN" else WEEKDAYS_CN.get(weekday_en, weekday_en)
                    next_day = {
                        "type": "workday",
                        "date": next_date.strftime("%m-%d"),
                        "name": today_status,
                        "days_away": (next_date - now.date()).days,
                    }
                    break
                next_date += datetime.timedelta(days=1)
        else:
            for _ in range(30):
                d_is_weekend = next_date.weekday() >= 5
                d_is_holiday = country_holidays.get(next_date)
                if d_is_weekend or d_is_holiday:
                    info = d_is_holiday if d_is_holiday else ("Saturday" if next_date.weekday() == 5 else "Sunday")
                    if self._lang == "EN":
                        label = info
                    else:
                        label = WEEKDAYS_CN.get(info, info) if isinstance(info, str) else info
                    next_day = {
                        "type": "rest",
                        "date": next_date.strftime("%m-%d"),
                        "name": label,
                        "days_away": (next_date - now.date()).days,
                    }
                    break
                next_date += datetime.timedelta(days=1)

        weekday_en = now.strftime("%A")
        weekday_disp = weekday_en if self._lang == "EN" else WEEKDAYS_CN.get(weekday_en, weekday_en)

        result = {
            "date_str": now.strftime("%Y-%m-%d"),
            "weekday": weekday_disp,
            "lunar": lunar_str,
            "is_rest_today": is_rest_today,
            "next_day": next_day,
        }
        self._cache.set("calendar_info", result)
        return result
