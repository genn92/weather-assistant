import datetime
from typing import cast

import streamlit as st
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from weather_assistant import config
from weather_assistant.agent import run_agent
from weather_assistant.tools.weather import DATE_RE, RELATIVE_FUTURE

st.set_page_config(page_title="天气助手 Agent", page_icon="🌤️")
st.title("🌤️ 天气查询 Agent")

client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_API_BASE_URL)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "你是一个天气查询助手，只能通过工具查询天气。"}
    ]

messages: list[ChatCompletionMessageParam] = cast(
    list[ChatCompletionMessageParam], st.session_state.messages
)


def render_history() -> None:
    for m in messages:
        content = m.get("content")
        if m["role"] in ("user", "assistant") and content:
            with st.chat_message(m["role"]):
                st.write(content)


def on_tool_call(name: str, args: dict) -> None:
    if name == "get_weather":
        with st.chat_message("assistant"):
            st.caption(f"🔧 正在查询 {args['city']} 天气...")
    elif name == "get_forecast":
        with st.chat_message("assistant"):
            st.caption(f"🔧 正在查询 {args['city']} 未来 {args.get('days', '')} 天的天气...")
    elif name == "get_daily_forecast":
        date = args.get("date", "")
        if date in RELATIVE_FUTURE or (
            DATE_RE.match(date) and date > datetime.date.today().isoformat()
        ):
            with st.chat_message("assistant"):
                st.caption(f"🔧 正在查询 {args['city']} {date} 的天气...")


render_history()

if prompt := st.chat_input("请输入城市，例如：北京今天天气怎么样？"):
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)
    start = len(messages)
    run_agent(client, messages, on_tool_call=on_tool_call)
    for m in messages[start:]:
        content = m.get("content")
        if m["role"] == "assistant" and content:
            with st.chat_message("assistant"):
                st.write(content)