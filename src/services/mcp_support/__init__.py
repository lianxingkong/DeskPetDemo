from .config import *

if app_config.base.is_enable:
    from . import base_mcp_tools
    from .example_mcp_config import *
    from .multi_mcp_manager import *

if app_config.base.is_enable:
    mcp_manager = MultiMCPManager()
else:
    mcp_manager = None


@base_mcp_tools.BaseMcpStart
async def mcp_start():
    if app_config.base.is_enable:
        global mcp_manager
        await mcp_manager.connect_all()

@base_mcp_tools.BaseMcpEnd
async def mcp_stop():
    if app_config.base.is_enable:
        global mcp_manager
        await mcp_manager.close_all()

# 连接mcp的桥接函数
async def call_mcp_tool_async(tool_name: str, arguments: dict, timeout: int = 15) -> str:
    """供外部 QThread 安全调用的桥接方法"""
    if not mcp_manager:
        return "错误：MCP 未启用"

    # 1. 构造要在 MCP 循环中执行的协程
    coro = mcp_manager.call_tool(tool_name, arguments)

    # 2. 提交到 MCP 后台循环
    future = base_mcp_tools.BaseMcpStart.call_async(coro)
    if future is None:
        return "错误：MCP 循环未启动"

    # 3. 将 concurrent.futures.Future 包装成当前循环可 await 的 Future
    try:
        asyncio_future = asyncio.wrap_future(future)
        result = await asyncio.wait_for(asyncio_future, timeout=timeout)
        return result
    except Exception as e:
        return f"调用出错: {e}"
