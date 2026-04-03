import requests
import datetime
import math
from .base import SimpleCache, ServiceProtocol


WMO_CN = {
    0: ("晴朗", "01d"), 1: ("多云", "02d"), 2: ("多云", "02d"), 3: ("阴天", "04d"),
    45: ("有雾", "50d"), 48: ("有雾", "50d"), 51: ("毛毛雨", "09d"), 53: ("毛毛雨", "09d"),
    55: ("毛毛雨", "09d"), 56: ("冻雨", "13d"), 57: ("冻雨", "13d"),
    61: ("小雨", "10d"), 63: ("中雨", "10d"), 65: ("大雨", "10d"),
    66: ("冻雨", "13d"), 67: ("冻雨", "13d"),
    71: ("小雪", "13d"), 73: ("中雪", "13d"), 75: ("大雪", "13d"),
    77: ("雪粒", "13d"),
    80: ("阵雨", "09d"), 81: ("阵雨", "09d"), 82: ("暴雨", "09d"),
    85: ("阵雪", "13d"), 86: ("阵雪", "13d"),
    95: ("雷雨", "11d"), 96: ("雷雨", "11d"), 99: ("雷雨", "11d"),
}
WMO_EN = {
    0: ("Clear", "01d"), 1: ("Cloudy", "02d"), 2: ("Cloudy", "02d"), 3: ("Overcast", "04d"),
    45: ("Fog", "50d"), 48: ("Fog", "50d"), 51: ("Drizzle", "09d"), 53: ("Drizzle", "09d"),
    55: ("Drizzle", "09d"), 56: ("Frz Driz", "13d"), 57: ("Frz Driz", "13d"),
    61: ("Rain", "10d"), 63: ("Rain", "10d"), 65: ("Hvy Rain", "10d"),
    66: ("Frz Rain", "13d"), 67: ("Frz Rain", "13d"),
    71: ("Snow", "13d"), 73: ("Snow", "13d"), 75: ("Hvy Snow", "13d"),
    77: ("Snow Grn", "13d"),
    80: ("Showers", "09d"), 81: ("Showers", "09d"), 82: ("Violent", "09d"),
    85: ("Snow Shw", "13d"), 86: ("Snow Shw", "13d"),
    95: ("T-Storm", "11d"), 96: ("Hail", "11d"), 99: ("Hail", "11d"),
}
RAIN_CODES = {61, 63, 65, 80, 81, 82, 66, 67}
SNOW_CODES = {71, 73, 75, 85, 86, 77}
STORM_CODES = {95, 96, 99}
DRIZZLE_CODES = {51, 53, 55}
ALL_PRECIP_CODES = RAIN_CODES | SNOW_CODES | STORM_CODES | DRIZZLE_CODES


def _map_wmo(code: int, lang: str) -> tuple[str, str]:
    m = WMO_EN if lang == "EN" else WMO_CN
    return m.get(code, ("未知" if lang != "EN" else "Unknown", "02d"))


def _precip_type(code: int, lang: str) -> str | None:
    if code in RAIN_CODES:
        return "雨" if lang != "EN" else "Rain"
    if code in SNOW_CODES:
        return "雪" if lang != "EN" else "Snow"
    if code in STORM_CODES:
        return "雷雨" if lang != "EN" else "T-Storm"
    if code in DRIZZLE_CODES:
        return "小雨" if lang != "EN" else "Drizzle"
    return None


class WeatherService:
    def __init__(self, latitude: float, longitude: float, timezone: str, language: str,
                 work_start: int, work_end: int, cache: SimpleCache):
        self._lat = latitude
        self._lon = longitude
        self._tz = timezone
        self._lang = language
        self._work_start = work_start
        self._work_end = work_end
        self._cache = cache

    @property
    def cache_ttl(self) -> int:
        return self._cache._ttl

    def fetch(self) -> dict:
        cached = self._cache.get(f"weather_{self._lat}_{self._lon}")
        if cached:
            return cached

        data = {
            "location": {"name": ""},
            "current": {
                "temp": "--", "humidity": "--", "desc": "N/A", "icon": "",
                "rain_chance": "--", "uv": "--", "aqi": "--",
                "aqi_level": "未知" if self._lang != "EN" else "Unknown",
                "high_low": "",
            },
            "forecast": [],
            "tomorrow": {"label": "", "icon": "", "temp": "", "desc": ""},
        }

        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self._lat,
                "longitude": self._lon,
                "current": "temperature_2m,relative_humidity_2m,weather_code,uv_index",
                "hourly": "temperature_2m,weather_code,precipitation_probability",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,uv_index_max",
                "timezone": self._tz,
            }
            resp = requests.get(url, params=params, timeout=10).json()

            current = resp.get("current", {})
            temp = round(current.get("temperature_2m", 0))
            hum = current.get("relative_humidity_2m", 0)
            code = current.get("weather_code", 0)
            uv_index = current.get("uv_index", 0)
            desc_text, icon = _map_wmo(code, self._lang)

            data["location"]["name"] = ""
            data["current"]["temp"] = temp
            data["current"]["humidity"] = f"{hum}%"
            data["current"]["desc"] = desc_text
            data["current"]["icon"] = icon
            data["current"]["uv"] = round(uv_index, 1) if uv_index else 0

            # AQI
            try:
                aqi_resp = requests.get(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    params={"latitude": self._lat, "longitude": self._lon,
                            "current": "pm2.5,pm10,us_aqi", "timezone": self._tz},
                    timeout=10,
                ).json()
                us_aqi = aqi_resp.get("current", {}).get("us_aqi", 0)
                data["current"]["aqi"] = us_aqi if us_aqi else "--"
                if us_aqi and us_aqi != "--":
                    if self._lang == "EN":
                        if us_aqi <= 50: level = "Good"
                        elif us_aqi <= 100: level = "Fair"
                        elif us_aqi <= 150: level = "Light"
                        elif us_aqi <= 200: level = "Mid"
                        elif us_aqi <= 300: level = "Bad"
                        else: level = "Hazard"
                    else:
                        if us_aqi <= 50: level = "优"
                        elif us_aqi <= 100: level = "良"
                        elif us_aqi <= 150: level = "轻度"
                        elif us_aqi <= 200: level = "中度"
                        elif us_aqi <= 300: level = "重度"
                        else: level = "严重"
                    data["current"]["aqi_level"] = level
            except Exception:
                pass

            hourly = resp.get("hourly", {})
            precip_probs = hourly.get("precipitation_probability", [])
            data["current"]["rain_chance"] = f"{precip_probs[0]}%" if precip_probs else "--"

            # Hourly forecast slots
            current_time_str = current.get("time")
            now_dt = datetime.datetime.fromisoformat(current_time_str)
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            codes = hourly.get("weather_code", [])

            def _idx_for(target_dt):
                for i, t_str in enumerate(times):
                    t_dt = datetime.datetime.fromisoformat(t_str)
                    if (t_dt.year == target_dt.year and t_dt.month == target_dt.month
                            and t_dt.day == target_dt.day and t_dt.hour == target_dt.hour):
                        return i
                return -1

            targets = []
            for offset in (1, 2):
                t = now_dt + datetime.timedelta(hours=offset)
                targets.append(t.replace(minute=0, second=0, microsecond=0))

            t3 = now_dt + datetime.timedelta(hours=3)
            t3 = t3.replace(minute=0, second=0, microsecond=0)
            work_start_dt = t3.replace(hour=self._work_start, minute=0, second=0, microsecond=0)
            work_end_dt = t3.replace(hour=self._work_end, minute=0, second=0, microsecond=0)
            if t3 < work_start_dt:
                t3 = work_start_dt
            elif t3 < work_end_dt:
                t3 = work_end_dt
            targets.append(t3)

            forecast_items = []
            for tgt in targets:
                idx = _idx_for(tgt)
                if idx != -1:
                    d_desc, icon = _map_wmo(codes[idx], self._lang)
                    forecast_items.append({
                        "label": tgt.strftime("%H:00"),
                        "icon": icon,
                        "temp": round(temps[idx]),
                        "desc": d_desc,
                    })
                else:
                    forecast_items.append({"label": tgt.strftime("%H:00"), "icon": "02d", "temp": "--", "desc": "N/A"})
            data["forecast"] = forecast_items

            # Tomorrow
            daily = resp.get("daily", {})
            if daily.get("time"):
                t_max = round(daily["temperature_2m_max"][0])
                t_min = round(daily["temperature_2m_min"][0])
                data["current"]["high_low"] = f"{t_max}° / {t_min}°"
            if len(daily.get("time", [])) >= 2:
                t_max = round(daily["temperature_2m_max"][1])
                t_min = round(daily["temperature_2m_min"][1])
                d_code = daily["weather_code"][1]
                d_desc, d_icon = _map_wmo(d_code, self._lang)
                label = "Tomorrow" if self._lang == "EN" else "明天"
                data["tomorrow"] = {
                    "label": label,
                    "icon": d_icon,
                    "temp": f"{t_max}/{t_min}°",
                    "desc": d_desc,
                }

            # Alert logic
            alert_msg = ""
            upcoming_alerts = []
            try:
                now_hour_idx = -1
                for i, t_str in enumerate(times):
                    t_dt = datetime.datetime.fromisoformat(t_str)
                    if t_dt.hour == now_dt.hour and t_dt.day == now_dt.day:
                        now_hour_idx = i
                        break
                if now_hour_idx != -1:
                    max_hours = min(now_hour_idx + 49, len(times))
                    curr_code = codes[now_hour_idx] if now_hour_idx < len(codes) else code
                    is_precip = curr_code in ALL_PRECIP_CODES
                    curr_precip = _precip_type(curr_code, self._lang)
                    if is_precip and curr_precip:
                        stop_hour = None
                        for i in range(now_hour_idx + 1, max_hours):
                            if codes[i] not in ALL_PRECIP_CODES:
                                stop_hour = i - now_hour_idx
                                break
                        if stop_hour:
                            if self._lang == "EN":
                                alert_msg = f"{curr_precip} stops in {stop_hour}H"
                            else:
                                alert_msg = f"{stop_hour}H后{curr_precip}停"
                        else:
                            remaining = max_hours - now_hour_idx - 1
                            if self._lang == "EN":
                                alert_msg = f"{curr_precip} for {remaining}H+"
                            else:
                                alert_msg = f"{curr_precip}将持续至少{remaining}H"
                    else:
                        for i in range(now_hour_idx + 1, max_hours):
                            t_dt = datetime.datetime.fromisoformat(times[i])
                            hours_from_now = i - now_hour_idx
                            wtype = _precip_type(codes[i], self._lang)
                            if wtype:
                                upcoming_alerts.append((hours_from_now, wtype, t_dt))
                        if upcoming_alerts:
                            first = upcoming_alerts[0]
                            hours, wtype, alert_dt = first
                            if self._lang == "EN":
                                alert_msg = f"{wtype} in {hours}h"
                            else:
                                alert_msg = f"{hours}H后有{wtype}"
            except Exception:
                pass

            data["current"]["alert"] = alert_msg
            data["current"]["has_warning"] = False
            data["current"]["upcoming_alerts"] = upcoming_alerts[:5]

        except Exception as e:
            print(f"Weather Error: {e}")

        self._cache.set(f"weather_{self._lat}_{self._lon}", data)
        return data
