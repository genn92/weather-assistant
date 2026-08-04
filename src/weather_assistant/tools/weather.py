from collections.abc import Callable

import requests
from openai.types.chat import ChatCompletionToolParam

TOOLS: list[ChatCompletionToolParam] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
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
    }
]


def get_weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=3"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.text.strip()
        return f"无法获取 {city} 的天气信息。"
    except requests.exceptions.RequestException as e:
        return f"获取 {city} 天气失败：{e}"


HANDLERS: dict[str, Callable[..., str]] = {
    "get_weather": get_weather,
}
