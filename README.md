# 天气查询 Agent

基于 **DeepSeek + Streamlit** 的天气查询 Agent，通过大模型的 Function Calling 能力自动调用天气工具回答用户问题。

## 功能特性

- 🌤️ 基于 DeepSeek Chat 模型，支持 Function Calling
- 🔧 内置 `get_weather` 工具，实时查询指定城市天气（数据源：wttr.in）
- 💬 Streamlit 聊天界面，实时展示工具调用过程
- ⚡ 使用 uv 管理依赖，开箱即用

## 技术栈

- Python 3.13+
- [DeepSeek](https://platform.deepseek.com/) API（OpenAI 兼容接口）
- [Streamlit](https://streamlit.io/)
- [uv](https://docs.astral.sh/uv/) 包管理

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

创建 `.env` 文件（可参考 `.env.example`）：

```bash
OPENAI_API_KEY=你的 DeepSeek API Key
OPENAI_API_BASE_URL=https://api.deepseek.com
```

### 3. 启动应用

```bash
uv run weather-assistant
```

启动后浏览器访问 http://localhost:8501。

## 使用方法

在聊天框中输入城市名称即可，例如：

- 「北京今天天气怎么样？」
- 「查询一下上海的天气」

Agent 会自动调用天气工具并返回查询结果。

## 项目结构

```
src/weather_assistant/
├── agent.py          # Agent 循环：对话与工具调用编排
├── app.py            # Streamlit 聊天界面
├── cli.py            # 命令行入口（启动 Streamlit）
├── config.py         # 环境变量配置
└── tools/
    └── weather.py    # 天气查询工具定义与实现
```

## License

MIT
