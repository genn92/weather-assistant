import datetime
import re
from collections.abc import Callable

import requests
from openai.types.chat import ChatCompletionToolParam

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

RELATIVE_DATES: dict[str, int] = {
    "今天": 0,
    "今日": 0,
    "明天": 1,
    "明日": 1,
    "后天": 2,
}

RELATIVE_FUTURE = ("明天", "明日", "后天")

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

FORECAST_DAYS = 16
MAX_FUTURE_DAYS = FORECAST_DAYS - 1

WEATHER_CODES: dict[int, str] = {
    0: "晴",
    1: "大致晴朗",
    2: "局部多云",
    3: "阴天",
    45: "雾",
    48: "冻雾",
    51: "小毛毛雨",
    53: "毛毛雨",
    55: "大毛毛雨",
    56: "小冻毛毛雨",
    57: "大冻毛毛雨",
    61: "小雨",
    63: "中雨",
    65: "大雨",
    66: "小冻雨",
    67: "大冻雨",
    71: "小雪",
    73: "中雪",
    75: "大雪",
    77: "雪粒",
    80: "小阵雨",
    81: "阵雨",
    82: "强阵雨",
    85: "小阵雪",
    86: "大阵雪",
    95: "雷暴",
    96: "雷暴伴小冰雹",
    99: "雷暴伴大冰雹",
}

TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市当前/此刻的实时天气。适用于用户问\"现在/今天(此刻)/实时\"天气。若用户问明天、后天或未来某一天，请使用 get_daily_forecast。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海",
                    }
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_forecast",
            "description": "查询指定城市未来某一天（明天、后天或未来 16 天内某天）的天气预报。date 参数支持\"明天\"\"后天\"等相对说法或具体日期。不要用它查询今天/此刻的实时天气，今天实时天气应使用 get_weather。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海",
                    },
                    "date": {
                        "type": "string",
                        "description": "查询日期，支持\"明天/后天\"等相对说法，或 YYYY-MM-DD 具体日期（如 2026-08-06）。请直接使用用户原话中的说法，不要自行换算日期。",
                    },
                },
                "required": ["city", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "查询指定城市从明天开始未来 N 天的天气预报，每天一行。适用于\"未来几天/未来一周\"等批量查询。今天的实时天气请用 get_weather。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，例如：北京、上海",
                    },
                    "days": {
                        "type": "integer",
                        "description": "查询天数，1~15，例如未来 7 天传 7",
                        "minimum": 1,
                        "maximum": 15,
                    },
                },
                "required": ["city", "days"],
            },
        },
    },
]


def get_weather(city: str) -> str:
    coords = _geocode(city)
    if coords is None:
        return f"无法找到城市：{city}。"
    lat, lon = coords

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "timezone": "auto",
    }
    try:
        res = requests.get(FORECAST_URL, params=params, timeout=10)
        if res.status_code != 200:
            return f"无法获取 {city} 的天气信息。"
        current = res.json()["current"]
        code = current["weather_code"]
        temp = current["temperature_2m"]
        humidity = current["relative_humidity_2m"]
        wind = current["wind_speed_10m"]
    except (requests.exceptions.RequestException, KeyError, ValueError) as e:
        return f"获取 {city} 天气失败：{e}"

    desc = WEATHER_CODES.get(code, f"代码 {code}")
    return (
        f"{city} 当前天气：{desc}，"
        f"气温 {temp}°C，"
        f"湿度 {humidity}%，"
        f"风速 {wind}km/h。"
    )


def get_daily_forecast(city: str, date: str) -> str:
    resolved = _resolve_date(date)
    if resolved is None:
        return f"日期参数无效：{date}。支持\"今天/明天/后天\"或 YYYY-MM-DD 格式。"
    date = resolved

    today = datetime.date.today().isoformat()
    if date < today:
        return (
            f"{date} 是过去的日期，无法提供天气预报。"
            f"今天的实时天气请用 get_weather 查询。"
        )
    if date == today:
        return f"{date} 是今天，实时/当前天气请用 get_weather 查询。"

    coords = _geocode(city)
    if coords is None:
        return f"无法找到城市：{city}。"
    lat, lon = coords

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        "weather_code,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": FORECAST_DAYS,
    }
    try:
        res = requests.get(FORECAST_URL, params=params, timeout=10)
        if res.status_code != 200:
            return f"无法获取 {city} 的天气信息。"
        daily = res.json()["daily"]
        times = daily["time"]
        if date not in times:
            listed = "、".join(times)
            return (
                f"{city} 在 {date} 没有预报数据。可查询的日期为：{listed}。"
                f"请用这些日期重新查询。"
            )
        idx = times.index(date)
        code = daily["weather_code"][idx]
        desc = WEATHER_CODES.get(code, f"代码 {code}")
        rain = daily["precipitation_probability_max"][idx]
        rain = f"{rain}%" if rain is not None else "未知"
        return (
            f"{city} {date} 天气：{desc}，"
            f"最高温 {daily['temperature_2m_max'][idx]}°C，"
            f"最低温 {daily['temperature_2m_min'][idx]}°C，"
            f"平均温 {daily['temperature_2m_mean'][idx]}°C，"
            f"降水概率最高 {rain}。"
        )
    except (requests.exceptions.RequestException, KeyError, ValueError, IndexError) as e:
        return f"获取 {city} 天气失败：{e}"


def get_forecast(city: str, days: int) -> str:
    try:
        days = int(days)
    except (TypeError, ValueError):
        return f"天数参数无效：{days}，请传入 1~{MAX_FUTURE_DAYS} 的整数。"
    if not 1 <= days <= MAX_FUTURE_DAYS:
        return f"天数超出范围：{days}，仅支持 1~{MAX_FUTURE_DAYS} 天。"

    coords = _geocode(city)
    if coords is None:
        return f"无法找到城市：{city}。"
    lat, lon = coords

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,"
        "weather_code,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": FORECAST_DAYS,
    }
    try:
        res = requests.get(FORECAST_URL, params=params, timeout=10)
        if res.status_code != 200:
            return f"无法获取 {city} 的天气信息。"
        daily = res.json()["daily"]
        times = daily["time"][1 : 1 + days]
        max_t = daily["temperature_2m_max"][1 : 1 + days]
        min_t = daily["temperature_2m_min"][1 : 1 + days]
        codes = daily["weather_code"][1 : 1 + days]
        rains = daily["precipitation_probability_max"][1 : 1 + days]
    except (requests.exceptions.RequestException, KeyError, ValueError, IndexError) as e:
        return f"获取 {city} 天气失败：{e}"

    lines = [
        f"{t} {WEATHER_CODES.get(code, f'代码 {code}')}，最高 {mx}°C，最低 {mn}°C，"
        f"降水概率 {rain}%"
        if rain is not None
        else f"{t} {WEATHER_CODES.get(code, f'代码 {code}')}，最高 {mx}°C，最低 {mn}°C，降水概率未知"
        for t, mx, mn, code, rain in zip(times, max_t, min_t, codes, rains)
    ]
    return f"{city} 未来 {len(lines)} 天天气预报（从明天开始）：\n" + "\n".join(lines)


def _resolve_date(date: str) -> str | None:
    if date in RELATIVE_DATES:
        offset = RELATIVE_DATES[date]
        return (datetime.date.today() + datetime.timedelta(days=offset)).isoformat()
    if DATE_RE.match(date):
        return date
    return None


def _geocode(city: str) -> tuple[float, float] | None:
    params = {"name": city, "count": 1}
    if not city.isascii():
        params["language"] = "zh"
    try:
        res = requests.get(GEOCODING_URL, params=params, timeout=10)
        if res.status_code != 200:
            return None
        results = res.json().get("results") or []
    except (requests.exceptions.RequestException, KeyError, ValueError):
        return None
    if not results:
        return None
    try:
        return results[0]["latitude"], results[0]["longitude"]
    except KeyError:
        return None


HANDLERS: dict[str, Callable[..., str]] = {
    "get_weather": get_weather,
    "get_daily_forecast": get_daily_forecast,
    "get_forecast": get_forecast,
}
