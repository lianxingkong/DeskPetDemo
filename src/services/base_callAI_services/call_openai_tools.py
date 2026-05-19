import asyncio

from loguru import logger
from PyQt5.QtCore import QObject, pyqtSignal

from ..base_callAI_services import *


class ChatToAI(QObject):
    # 定义信号：接收到一段流式文本 / 全部生成完毕
    message_received = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()

    def fetch_data(self, msg):
        """
        这个方法将在子线程中执行。
        """
        # 在子线程中开启异步事件循环
        asyncio.run(self._async_fetch(msg))

    async def _async_fetch(self, msg):
        try:
            logger.debug("开始提交问题")
            # 发送带有流式输出的请求 (你的原代码)
            response = await client.chat.completions.create(
                model="Pro/deepseek-ai/DeepSeek-V3.2",
                messages=[{"role": "system", "content": system_promote},
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
