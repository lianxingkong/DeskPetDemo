import asyncio
import threading
from functools import wraps
from loguru import logger


class BaseMcpStart:
    """mcp的类装饰器(启动) + 异步循环管理器"""
    _registry = []

    # ===== 新增：类属性，持有专属的异步循环和线程 =====
    # AbstractEventLoop是所有事件循环的基类
    _loop: asyncio.AbstractEventLoop = None
    _loop_thread: threading.Thread = None

    def __init__(self, func):
        self.func = func
        wraps(func)(self)
        BaseMcpStart._registry.append(self.func)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    # ===== 新增：启动并维护后台 asyncio 循环 =====
    @classmethod
    def start_loop(cls):
        if cls._loop is not None and cls._loop.is_running():
            logger.debug("MCP Async Loop 已经在运行")
            return

        def _run_loop():
            # 创建一个新的事件循环
            cls._loop = asyncio.new_event_loop()
            # 设置为当前事件循环
            asyncio.set_event_loop(cls._loop)
            # 执行事件直到close()
            cls._loop.run_forever()  # 此处阻塞，线程一直存活
            logger.debug("MCP Async Loop 已退出")

        cls._loop_thread = threading.Thread(target=_run_loop, daemon=True)
        cls._loop_thread.start()

        # 等待 loop 被创建 (极其短暂的时间)
        while cls._loop is None:
            pass

    # ===== 新增：供外部安全调用异步函数的接口 =====

    @classmethod
    def call_async(cls, coro):
        """外部通过此方法将协程提交给 MCP 的后台循环执行"""
        # cls表示输入参数，用._loop(继承自AbstractEventLoop的事件循环基类)来进行事件循环操作
        if cls._loop is None or not cls._loop.is_running():
            logger.error("MCP Loop 未启动，无法执行异步任务")
            return None
        return asyncio.run_coroutine_threadsafe(coro, cls._loop)

    @classmethod
    def start_all(cls):
        """执行所有已注册的函数"""
        if cls._loop is None:
            raise RuntimeError("必须先调用 BaseMcpStart.start_loop() 启动循环！")

        logger.debug("开始启动所有 MCP 服务...")
        for func in cls._registry:
            if asyncio.iscoroutinefunction(func):
                # 将异步函数提交给本类管理的 loop
                asyncio.run_coroutine_threadsafe(func(), cls._loop)
            else:
                func()


class BaseMcpEnd:
    """mcp的类装饰器(结束)"""
    _registry = []

    def __init__(self, func):
        self.func = func
        wraps(func)(self)
        BaseMcpEnd._registry.append(self.func)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @classmethod
    def start_all(cls):
        """执行所有已注册的函数"""
        if BaseMcpStart._loop is None:
            return

        logger.debug("开始停止所有 MCP 服务...")
        for func in cls._registry:
            if asyncio.iscoroutinefunction(func):
                asyncio.run_coroutine_threadsafe(func(), BaseMcpStart._loop)
            else:
                func()

        # 稍微给一点时间让关闭协程执行，然后关闭整个 loop
        import time
        time.sleep(1)
        BaseMcpStart._loop.call_soon_threadsafe(BaseMcpStart._loop.stop)
