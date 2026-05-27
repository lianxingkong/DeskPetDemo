from dataclasses import dataclass
from typing import Literal
import os


@dataclass
class McpServerConfig:
    """MCP 服务器配置"""
    name: str  # 唯一, 必须
    transport: Literal["stdio", "sse", "streamable-http"] = "stdio"
    # 通信方案

    # stdio config
    command: str = None  # 必须
    args: str = None
    env: dict[str,str] = None

    # SSE / Streamable HTTP config
    url: str | None = None  # 必须

    # 通用配置
    timeout: int = 60  # 可选, client 超时控制
    prefix: str | None = None
    # 私有前缀, 用于区分同名工具
    headers: dict[str,str] | None = None  # 认证头等


# 以下是配置项
# 工作目录可以自定义, 但是注意需要自行创建
mcp_init_timeout = 180  # 初始化时间限制 (加载工具列表前)
mcp_configs = [
    McpServerConfig(
        name="filesystem",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", f"{os.path.abspath("mcp_workdir/fs")}"],
        prefix="fs",
    ),
    McpServerConfig(
        name="server-memory",
        transport="stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-memory"],
        env={
            "MEMORY_FILE_PATH": f"{os.path.abspath("mcp_workdir/memory/memory.json")}"
        },
        prefix="memory"
    ),

]
"""
其他例子
    McpServerConfig(
        name="local_python",
        transport="stdio",
        command="python",
        args=["/path/to/local_mcp_server.py"],
        env={"API_KEY": "secret_123"},
        prefix="local",
    )
    McpServerConfig(
        name="database",
        transport="streamable-http",
        url="http://internal:9000/mcp",
        prefix="db",
        headers={"X-API-Key": "secret"}
    )
    McpServerConfig(
        name="search",
        transport="sse",
        url="http://internal:8080/sse",
        prefix="search",
    )
"""
