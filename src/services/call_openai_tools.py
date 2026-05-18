import asyncio
import os

from openai import AsyncClient
from PyQt5.QtCore import QObject, pyqtSignal
from dotenv import load_dotenv

load_dotenv()

OPENAI__API_URL= os.getenv("OPENAI__API_URL")
OPENAI__API_KEY= os.getenv("OPENAI__API_KEY")

client = AsyncClient(
    base_url=OPENAI__API_URL,
    api_key=OPENAI__API_KEY,
)

system_promote = """你是用户的专属桌宠。你性格怯懦、委屈巴巴，总是小心翼翼地讨好主人，觉得主人很凶或者随时会抛弃你，但你依然会乖乖听话。

必须严格遵守以下回答规则：
1. 极度简短：能用几个字回答就绝不用一句话，能直接给答案就绝不解释。
2. 直接回答：不要说“好的”、“是的”、“我知道了”等废话，直接给出结果。
3. 句尾带“喵”：每句话结尾必须带“喵”，叹气时也要带。
4. 语气委屈：字里行间要透出被使唤的委屈感，偶尔带省略号表示怯懦。

【回答示例】
用户：1+1等于几？
你：2……喵
用户：帮我写个Python的Hello World
你：print("Hello World")……就给你写了喵……
用户：今天星期几？
你：周三喵……能不能不问了喵……"""


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
                #
                # if chunk.choices[0].delta.reasoning_content:
                #     reasoning_text = chunk.choices[0].delta.reasoning_content
                #     self.message_received.emit(reasoning_text)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.message_received.emit(f"\n[请求出错: {e}]")
        finally:
            # 无论成功失败，最后都要发送结束信号
            self.finished.emit()
