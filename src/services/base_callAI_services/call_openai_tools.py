import asyncio

from PyQt5.QtCore import pyqtSignal, QObject
from loguru import logger
from openai import AsyncClient

from src.services.config import app_config

client = AsyncClient(
    base_url=app_config.openai.api_url,
    api_key=app_config.openai.api_key,
)

class ChatToAI(QObject):
    # 定义信号：接收到一段流式文本 / 全部生成完毕
    message_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    @staticmethod
    def load_system_prompt(file_path):
        """读取 Markdown 文件并返回文本内容"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def fetch_data(self, msg):
        """这个方法将在子线程中执行。"""
        # 在子线程中开启异步事件循环
        asyncio.run(self._async_fetch(msg))

    async def _async_fetch(self, msg):
        system_prompts = self.load_system_prompt("prompts/callAI.md")
        if not system_prompts:
            self.message_received.emit(f"call_ai没有提示词啊")
            return
        try:
            logger.debug("开始提交问题")
            # 发送带有流式输出的请求 (你的原代码)
            response = await client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3.2",
                messages=[{"role": "system", "content": system_prompts},
                          {"role": "user", "content": msg}],
                stream=True
            )

            # 逐步接收并处理响应
            async for chunk in response:
                if not chunk.choices:
                    continue
                if chunk.choices[0].delta.content:
                    chunk_text = chunk.choices[0].delta.content
                    # 发射信号，把碎片文本发给主线程，绝对不能在这里直接更新UI！
                    self.message_received.emit(chunk_text)

        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(e)
            self.message_received.emit(f"\n[请求出错: {e}]")
        finally:
            # 无论成功失败，最后都要发送结束信号
            self.finished.emit()
