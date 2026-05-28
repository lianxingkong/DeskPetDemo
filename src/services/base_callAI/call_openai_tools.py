import asyncio
import json

from PyQt5.QtCore import pyqtSignal, QObject
from loguru import logger
from openai import AsyncClient

from .config import app_config
from src.services.mcp_support import call_mcp_tool_async, mcp_manager  # 导入桥接方法和实例

client = AsyncClient(
    base_url=app_config.openai.api_url,
    api_key=app_config.openai.api_key,
)


class ChatToAI(QObject):
    message_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    @staticmethod
    def load_system_prompt(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def fetch_data(self, msg):
        asyncio.run(self._async_fetch(msg))

    async def _async_fetch(self, msg):
        system_prompts = self.load_system_prompt("prompts/callAI.md")
        if not system_prompts:
            self.message_received.emit("call_ai没有给系统提示词啊")
            return

        # 🚨 关键1：获取 MCP 当前注册的所有工具列表 (读内存即可，不需要桥接)
        mcp_tools = mcp_manager.all_tools if mcp_manager else []

        messages = [
            {"role": "system", "content": system_prompts},
            {"role": "user", "content": msg}
        ]

        try:
            logger.debug("开始提交问题 (第一轮：判断是否需要调用工具)")
            # 🚨 关键2：将 tools 传给大模型
            response = await client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3.2",
                messages=messages,
                tools=mcp_tools if mcp_tools else None,
                stream=True
            )

            # 收集流式返回的工具调用参数
            tool_calls = []
            text_content = ""
            finish_reason = None

            async for chunk in response:
                if not chunk.choices:
                    continue

                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason

                # 正常文本输出
                if delta.content:
                    if not delta.content.strip() and not text_content:
                        continue
                    self.message_received.emit(delta.content)
                    text_content += delta.content

                # 🚨 关键3：收集工具调用碎片
                if delta.tool_calls:
                    for tc_chunk in delta.tool_calls:
                        idx = tc_chunk.index
                        # 动态扩充列表以容纳可能的多工具调用
                        while len(tool_calls) <= idx:
                            tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})

                        if tc_chunk.id:
                            tool_calls[idx]["id"] = tc_chunk.id
                        if tc_chunk.function.name:
                            tool_calls[idx]["function"]["name"] += tc_chunk.function.name
                        if tc_chunk.function.arguments:
                            tool_calls[idx]["function"]["arguments"] += tc_chunk.function.arguments

            # 🚨 关键4：如果大模型决定调用工具
            if finish_reason == "tool_calls" and tool_calls:
                # 把大模型的工具调用决议加入历史
                messages.append({
                    "role": "assistant",
                    "tool_calls": tool_calls
                })

                # 逐个执行工具
                for tc in tool_calls:
                    func_name = tc["function"]["name"]
                    try:
                        func_args = json.loads(tc["function"]["arguments"])
                    except:
                        func_args = {}

                    # 通知 UI 正在执行动作
                    self.message_received.emit(f"[正在执行工具: {func_name}...]\n")
                    logger.debug(f"AI 决定调用工具: {func_name}, 参数: {func_args}")

                    # 使用桥接方法安全调用 MCP 工具
                    tool_result = await call_mcp_tool_async(func_name, func_args)

                    # 把工具结果加入历史
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": str(tool_result)
                    })

                # 🚨 关键5：带着工具结果，进行第二轮请求，让大模型总结
                logger.debug("开始提交问题 (第二轮：带工具结果总结)")
                second_response = await client.chat.completions.create(
                    model="Pro/deepseek-ai/DeepSeek-V3.2",
                    messages=messages,
                    stream=True
                    # 第二轮一般不需要再传 tools，让它专心根据结果回答即可
                )

                async for chunk in second_response:
                    if not chunk.choices:
                        continue
                    if chunk.choices[0].delta.content:
                        self.message_received.emit(chunk.choices[0].delta.content)

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(e)
            self.message_received.emit(f"\n[请求出错: {e}]")
        finally:
            self.finished.emit()
