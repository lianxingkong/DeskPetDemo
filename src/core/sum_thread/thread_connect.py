import asyncio
import threading

from loguru import logger

from src.services.mcp_support.base_mcp_tools import BaseMcpStart, BaseMcpEnd
from src.services.voice_recognize import WhisperSegment
from src.services.memory_manage import HandleMemory
from src.services.image_recognize import Report_request
from src.services.base_callAI import ChatToAI
from src.services.monitor_screen import Monitor_Screen


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
        self.text_loop = None  # 保存子线程的事件循环
        self.img_loop = None
        self.voice_loop = None
        self.path = None    # 保存图片地址
        self.queue = None   # text 获取回复信息队列
        self.msg_queue = None   # text 返回回复信息至气泡上显示
        self.img_queue = None   # img 获取输入的图片地址
        self.result_queue = None    # img 传递识别的图片信息
        self.ai_msg_queue = None    # img 传递识别的信息与用户的问题
        self.end_signal_queue = None    # img 传递返回的结果显示在气泡上
        self.get_data_queue = None  # voice 获取音频识别后的原始数据
        self.voice_queue = None     # voice 分析原始数据并返回并传递识别文本
        self.answer_queue = None    # voice 将结果显示在气泡上


        self.status = False # 默认无操作时为False

        # 初始化注册列表
        self.callback_list = []

        # 实例化 Worker
        self.chat_worker = ChatToAI()
        self.voice_worker = WhisperSegment()
        self.photo_worker = Report_request()
        self.memory_worker = HandleMemory()
        self.monitor_woker = Monitor_Screen()

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
        self.end_signal_queue = asyncio.Queue()

        # 执行异步初始化
        self.img_loop.run_until_complete(self._run_photo_tasks())

    def _init_voice_thread(self):
        """音频处理子线程"""
        self.voice_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.voice_loop)

        self.get_data_queue = asyncio.Queue()
        self.voice_queue = asyncio.Queue()
        self.answer_queue = asyncio.Queue()

        # 初始化语音模型
        self.voice_loop.run_until_complete(self.voice_worker.load_model())
        # 执行异步初始化
        self.voice_loop.run_until_complete(self._run_voice_tasks())


    async def _run_photo_tasks(self):
        """img 并发运行输入和输出队列的监听任务"""
        self._end_monitor = asyncio.create_task(self.put_end_signal(self.end_signal_queue))
        self._monitor = asyncio.create_task(self.monitor_woker.base_monitor(self.img_queue, self.end_signal_queue))
        self._fetch_img = asyncio.create_task(self.photo_worker.start_process(self.img_queue, self.result_queue))
        self._ai_msg = asyncio.create_task(self.chat_worker.fetch_data(self.result_queue, self.ai_msg_queue))
        self._img_replay = asyncio.create_task(self.replay_data(self.ai_msg_queue))
        await asyncio.gather(self._monitor, self._fetch_img, self._img_replay, self._ai_msg)

    async def _run_text_tasks(self):
        """text 并发运行输入和输出队列的监听任务"""
        self._fetch_msg = asyncio.create_task(self.chat_worker.fetch_data(self.queue, self.msg_queue))
        self._text_replay = asyncio.create_task(self.replay_data(self.msg_queue))
        await asyncio.gather(self._fetch_msg, self._text_replay)

    async def _run_voice_tasks(self):
        """voice 并发运行输入和输出队列的监听任务"""
        self._fetch_voice = asyncio.create_task(self.voice_worker.fasterWhisperSegment(self.get_data_queue, self.voice_queue))
        self._voice_result = asyncio.create_task(self.chat_worker.fetch_data(self.get_data_queue, self.answer_queue))
        self._voice_replay = asyncio.create_task(self.replay_data(self.answer_queue))
        await asyncio.gather(self._fetch_voice, self._voice_result, self._voice_replay)

    def send_text_to_queue(self, msg):
        """供主线程调用，将数据安全地放入子线程的队列"""
        if self.queue is None or self.text_loop is None:
            print("子线程尚未准备就绪")
            return

        self.status = True  # 激活
        # 使用 call_soon_threadsafe 跨线程安全地提交协程
        async def _put():
            await self.queue.put((msg, None, False))

        self.text_loop.call_soon_threadsafe(lambda: asyncio.create_task(_put()))

    def send_image_to_queue(self, path):
        """供主线程调用，将数据安全地放入子线程的队列"""
        if self.img_queue is None or self.img_loop is None:
            print("子线程尚未准备就绪")
            return

        self.status = True  # 激活
        # 使用 call_soon_threadsafe 跨线程安全地提交协程
        _list = [path, None, False]
        async def _put():
            await self.img_queue.put(_list)

        self.img_loop.call_soon_threadsafe(lambda: asyncio.create_task(_put()))

    def send_voice_to_queue(self, audio_data):
        """供主线程调用，将数据安全地放入子线程的队列"""
        if self.voice_queue is None or self.voice_loop is None:
            print("子线程尚未准备就绪")
            return

        self.status = True  # 激活
        # 使用 call_soon_threadsafe 跨线程安全地提交协程
        async def _put():
            await self.voice_queue.put(audio_data)

        self.voice_loop.call_soon_threadsafe(lambda: asyncio.create_task(_put()))


    async def put_end_signal(self, end_signal_queue):
        """传回目前用户是否进行操作的状态信号"""
        while True:
            try:
                await asyncio.sleep(1)  # 主动休眠 1 秒
                if end_signal_queue.empty():
                    await end_signal_queue.put(self.status)
                else:
                    await end_signal_queue.get()    # 消费掉一个，保证队列里只有一个
                    assert end_signal_queue.qsize() == 0    # 断言此时刻没有元素
                    await end_signal_queue.put(self.status)
            except Exception as e:
                logger.error(e)


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
                _msg = await all_queue.get()
                logger.debug(_msg)
                msg = _msg[0]
                st = _msg[1]
                all_queue.task_done()
                # 广播信息
                self.callback_ui(msg)
                self.status = st
                logger.debug(self.status)
        except Exception as e:
            logger.error(f"{e}")
            import traceback
            traceback.print_exc()


    def cleanup(self):
        """清理事件，退出MCP服务"""
        self._end_monitor.cancel()
        self._monitor.cancel()
        self._fetch_img.cancel()
        self._ai_msg.cancel()
        self._img_replay.cancel()
        self._fetch_msg.cancel()
        self._text_replay.cancel()
        self._fetch_voice.cancel()
        self._voice_result.cancel()
        self._voice_replay.cancel()
        BaseMcpEnd.start_all()
