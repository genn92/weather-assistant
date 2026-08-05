import datetime
import json
import re
from collections.abc import Callable

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from weather_assistant.tools.weather import HANDLERS, TOOLS

ToolCallCallback = Callable[[str, dict], None]

MAX_ITERATIONS = 10
DATE_INSTRUCTION = (
    "今天的日期是 {today}，明天是 {tomorrow}。用户问\"今天/现在/当前/实时\"天气 → "
    "调用 get_weather；问\"明天/后天\"或具体某一天 → 直接按用户原话把\"明天\"/\"后天\""
    "作为 date 参数传给 get_daily_forecast；问\"未来几天/未来一周\"等 → 用 get_forecast "
    "一次性查询。不要自行换算日期，也不要向用户询问日期。"
)


def run_agent(
    client: OpenAI,
    messages: list[ChatCompletionMessageParam],
    on_tool_call: ToolCallCallback | None = None,
) -> list[ChatCompletionMessageParam]:
    """执行 agent 循环，将对话与工具调用结果追加到 messages 并返回。

    on_tool_call 可选回调，签名为 (tool_name, arguments)，用于 UI 反馈。
    """
    _inject_today(messages)

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=TOOLS
        )
        msg = response.choices[0].message
        first = next(
            (tc for tc in (msg.tool_calls or []) if tc.type == "function"), None
        )

        if first is None:
            messages.append({"role": "assistant", "content": msg.content})
            return messages

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": first.id,
                        "type": "function",
                        "function": {
                            "name": first.function.name,
                            "arguments": first.function.arguments,
                        },
                    }
                ],
            }
        )

        try:
            args = json.loads(first.function.arguments)
        except json.JSONDecodeError:
            result = (
                f"工具参数解析失败：{first.function.arguments!r}，"
                f"请用合法 JSON 重新调用 {first.function.name}。"
            )
        else:
            try:
                if on_tool_call:
                    on_tool_call(first.function.name, args)
                handler = HANDLERS.get(first.function.name)
                result = (
                    handler(**args)
                    if handler
                    else f"未知工具：{first.function.name}"
                )
            except (TypeError, KeyError) as e:
                result = (
                    f"调用 {first.function.name} 参数有误：{e}。"
                    f"请按工具参数规范重新调用。"
                )
        messages.append({"role": "tool", "tool_call_id": first.id, "content": result})

    messages.append(
        {"role": "assistant", "content": "已达到最大工具调用次数，请基于已有信息回答。"}
    )
    return messages


def _inject_today(messages: list[ChatCompletionMessageParam]) -> None:
    today = datetime.date.today().isoformat()
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
    date_pat = re.compile(r"今天的日期是 \d{4}-\d{2}-\d{2}，明天是 \d{4}-\d{2}-\d{2}。")
    for m in messages:
        if m.get("role") != "system":
            continue
        content = m.get("content")
        if isinstance(content, str):
            sentence = f"今天的日期是 {today}，明天是 {tomorrow}。"
            if date_pat.search(content):
                content = date_pat.sub(sentence, content)
            else:
                content = content + DATE_INSTRUCTION.format(today=today, tomorrow=tomorrow)
            m["content"] = content
        break
