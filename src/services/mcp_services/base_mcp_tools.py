from functools import wraps


class BaseMcpStart:
    """mcp的类装饰器(启动)"""
    # 定义注册表(我不到你要装饰几个啊)
    _registry = []

    def __init__(self, func):
        self.func = func
        wraps(func)(self)  # 保留元信息
        BaseMcpStart._registry.append(self.func)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @classmethod
    def start_all(cls):
        """执行所有已注册的函数"""
        for func in cls._registry:
            func()

class BaseMcpEnd:
    """mcp的类装饰器(结束)"""
    # 定义注册表
    _registry = []

    def __init__(self, func):
        self.func = func
        wraps(func)(self)  # 保留元信息
        BaseMcpEnd._registry.append(self.func)

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    @classmethod
    def start_all(cls):
        """执行所有已注册的函数"""
        for func in cls._registry:
            func()
