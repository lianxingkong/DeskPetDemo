import json

from loguru import logger
from openai import AsyncClient

from .config import app_config
from src.services.mcp_support import call_mcp_tool_async, mcp_manager  # 导入桥接方法和实例
from src.services.memory_manage.memory_tools import HandleMemory
from src.core.methods_tools import BaseAIRetry


client = AsyncClient(
    base_url=app_config.openai.api_url,
    api_key=app_config.openai.api_key,
    timeout=15
)

class ChatToAI():

    def __init__(self):
        super().__init__()
        self.memory = HandleMemory()
        self.img_message = None
        self.replay = None
        self.img_message = None  # 初始化图片信息(如果有)

    @staticmethod
    def load_system_prompt(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    async def fetch_data(self, get_original_queue, put_result_queue):
        """启动AI回复的中继"""
        try:
            while True:
                msg = await get_original_queue.get()

                # 防御性检查
                if not msg or len(msg) < 3:
                    get_original_queue.task_done()
                    continue

                text = msg[0]
                msg_type = msg[1]  # 'img' 或 None
                st = msg[2]  # window_title(监听) 或 False(普通)
                logger.debug(f"fetch_data获取到的消息: {msg}")
                if msg_type == "img" and st:
                    if text:
                        await self._async_fetch(text, put_result_queue, st)
                    self.img_message = None
                elif msg_type == "img" and not st:
                    self.img_message = text
                    await put_result_queue.put("看到图片了，你想问什么")
                elif msg_type is None:
                    if text:
                        final_text = text
                        if self.img_message:
                            final_text = f"图片信息：{self.img_message}\n用户问题：{text}"
                            self.img_message = None

                        await self._async_fetch(final_text, put_result_queue, st)

                get_original_queue.task_done()
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(e)

    @BaseAIRetry(max_frequency = 3, delay = 0)
    async def _async_fetch(self, final_text, put_result_queue, st):
        # 这里_msg不要重名，好像传入方法的参数优先级最高
        msg = await self.memory.query_memory(final_text)
        monitor_prompts = self.load_system_prompt("prompts/monitor.md")
        system_prompts = self.load_system_prompt("prompts/callAI.md")
        if not system_prompts or not monitor_prompts:
            logger.error("call_ai没有给系统提示词啊")
            raise "call_ai没有给系统提示词啊"

        # 🚨 关键1：获取 MCP 当前注册的所有工具列表 (读内存即可，不需要桥接)
        mcp_tools = mcp_manager.all_tools if mcp_manager else []

        # 命中监听屏幕
        _prompts = monitor_prompts if st else system_prompts

        messages = [
            {"role": "system", "content": _prompts},
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
                    await put_result_queue.put([delta.content, True])
                    logger.debug([delta.content, True])
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
                    await put_result_queue.put([f"[正在执行工具: {func_name}...]\n", True])
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
                        text_content = chunk.choices[0].delta.content
                        await put_result_queue.put([text_content, True])

            await self.memory.to_ai_memory(text_content)
            await put_result_queue.put([" ", False])

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(e)
            await put_result_queue.put([f"\n[请求出错: {e}]", True])
