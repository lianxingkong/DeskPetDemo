import asyncio
import threading

from loguru import logger

from src.services.mcp_support.base_mcp_tools import BaseMcpStart, BaseMcpEnd
from src.services.voice_recognize import WhisperSegment, AsyncVoiceRecorder
from src.services.memory_manage import HandleMemory
from src.services.image_recognize import Report_request
from src.services.base_callAI import ChatToAI


class ThreadManager:
    # ===== 1. 增加单例模式，确保全局唯一 =====
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 防止重复初始化
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        super().__init__()
        self.fetch_msg = None
        self.fetch_img = None
        self.fetch_voice = None
        self.queue = None  # 提前定义队列属性
        self.text_loop = None  # 保存子线程的事件循环
        self.img_loop = None
        self.voice_loop = None
        self.path = None    # 保存图片地址

        # 初始化注册列表
        self.callback_list = []

        # 实例化 Worker
        self.chat_worker = ChatToAI()
        self.voice_worker = WhisperSegment()
        self.photo_worker = Report_request()
        self.memory_worker = HandleMemory()

        # 启动线程
        self.t1 = threading.Thread(target=self._init_text_thread, daemon=True)
        self.t1.start()

        self.t2 = threading.Thread(target=self._init_photo_thread, daemon=True)
        self.t2.start()

        self.t3 = threading.Thread(target=self._init_voice_thread, daemon=True)
        self.t3.start()

        BaseMcpStart.start_loop()
        BaseMcpStart.start_all()

    def _init_text_thread(self):
        """AI回复子线程"""
        self.text_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.text_loop)

        # 在事件循环中创建 Queue
        self.queue = asyncio.Queue()
        self.msg_queue = asyncio.Queue()

        # 执行异步初始化
        # 这是阻塞的，协程未结束是不会停止的
        self.text_loop.run_until_complete(self._run_text_tasks())

    def _init_photo_thread(self):
        """图片处理的子线程"""
        self.img_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.img_loop)

        self.img_queue = asyncio.Queue()
        self.result_queue = asyncio.Queue()
        self.ai_msg_queue = asyncio.Queue()

        # 执行异步初始化
        self.img_loop.run_until_complete(self._run_photo_tasks())

    def _init_voice_thread(self):
        """音频处理子线程"""
        self.voice_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.voice_loop)

        self.get_queue = asyncio.Queue()
        self.voice_queue = asyncio.Queue()
        self.answer_queue = asyncio.Queue()

        # 初始化语音模型
        self.voice_loop.run_until_complete(self.voice_worker.load_model())
        # 执行异步初始化
        self.voice_loop.run_until_complete(self._run_voice_tasks())


    async def _run_photo_tasks(self):
        """img 并发运行输入和输出队列的监听任务"""
        self.fetch_img = asyncio.create_task(self.photo_worker.start_process(self.img_queue, self.result_queue))
        self.ai_msg = asyncio.create_task(self.chat_worker.fetch_data(self.result_queue, self.ai_msg_queue))
        self.replay = asyncio.create_task(self.replay_data(self.ai_msg_queue))
        await asyncio.gather(self.fetch_img, self.replay, self.ai_msg)

    async def _run_text_tasks(self):
        """text 并发运行输入和输出队列的监听任务"""
        self.fetch_msg = asyncio.create_task(self.chat_worker.fetch_data(self.queue, self.msg_queue))
        self.replay = asyncio.create_task(self.replay_data(self.msg_queue))
        await asyncio.gather(self.fetch_msg, self.replay)

    async def _run_voice_tasks(self):
        """voice 并发运行输入和输出队列的监听任务"""
        self.fetch_voice = asyncio.create_task(self.voice_worker.fasterWhisperSegment(self.get_queue, self.voice_queue))
        self._voice_result = asyncio.create_task(self.chat_worker.fetch_data(self.get_queue, self.answer_queue))
        self.replay = asyncio.create_task(self.replay_data(self.answer_queue))
        await asyncio.gather(self.fetch_voice, self._voice_result, self.replay)


    def send_text_to_queue(self, msg):
        """供主线程调用，将数据安全地放入子线程的队列"""
        if self.queue is None or self.text_loop is None:
            print("子线程尚未准备就绪")
            return

        # 使用 call_soon_threadsafe 跨线程安全地提交协程
        async def _put():
            await self.queue.put((msg, None))

        self.text_loop.call_soon_threadsafe(lambda: asyncio.create_task(_put()))

    def send_image_to_queue(self, path):
        """供主线程调用，将数据安全地放入子线程的队列"""
        if self.img_queue is None or self.img_loop is None:
            print("子线程尚未准备就绪")
            return

        # 使用 call_soon_threadsafe 跨线程安全地提交协程
        async def _put():
            await self.img_queue.put(path)

        self.img_loop.call_soon_threadsafe(lambda: asyncio.create_task(_put()))

    def send_voice_to_queue(self, audio_data):
        """供主线程调用，将数据安全地放入子线程的队列"""
        if self.voice_queue is None or self.voice_loop is None:
            print("子线程尚未准备就绪")
            return

        # 使用 call_soon_threadsafe 跨线程安全地提交协程
        async def _put():
            await self.voice_queue.put(audio_data)

        self.voice_loop.call_soon_threadsafe(lambda: asyncio.create_task(_put()))

    def callback_ui(self, msg):
        """广播获取到的信息"""
        for cb in self.callback_list:
            cb(msg)

    def _on_callback(self, callback):
        """加入广播列表"""
        self.callback_list.append(callback)

    def _out_callback(self, callback):
        """退出广播列表"""
        self.callback_list.remove(callback)

    async def replay_data(self, all_queue):
        """向在列表的方法广播信息,将展示信息传回UI展示"""
        try:
            while True:
                msg = await all_queue.get()
                all_queue.task_done()
                # 广播信息
                self.callback_ui(msg)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(e)


    def cleanup(self):
        self.fetch_msg.cancel()
        self.fetch_img.cancel()
        self.fetch_voice.cancel()
        BaseMcpEnd.start_all()
