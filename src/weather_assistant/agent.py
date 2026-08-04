import json
from collections.abc import Callable

from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from weather_assistant.tools.weather import HANDLERS, TOOLS

ToolCallCallback = Callable[[str, dict], None]


def run_agent(
    client: OpenAI,
    messages: list[ChatCompletionMessageParam],
    on_tool_call: ToolCallCallback | None = None,
) -> list[ChatCompletionMessageParam]:
    """执行 agent 循环，将对话与工具调用结果追加到 messages 并返回。

    on_tool_call 可选回调，签名为 (tool_name, arguments)，用于 UI 反馈。
    """
    while True:
        response = client.chat.completions.create(
            model="deepseek-chat", messages=messages, tools=TOOLS
        )
        msg = response.choices[0].message
        tool_calls = msg.tool_calls or []

        if not tool_calls:
            messages.append({"role": "assistant", "content": msg.content})
            return messages

        messages.append(
            {
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                    if tc.type == "function"
                ],
            }
        )

        for tc in tool_calls:
            if tc.type != "function":
                continue
            args = json.loads(tc.function.arguments)
            if on_tool_call:
                on_tool_call(tc.function.name, args)
            handler = HANDLERS.get(tc.function.name)
            result = handler(**args) if handler else f"未知工具：{tc.function.name}"
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
