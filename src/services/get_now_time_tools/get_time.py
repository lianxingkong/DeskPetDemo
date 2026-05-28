from datetime import datetime

from mcp.server.fastmcp import FastMCP

# 初始化服务器
mcp = FastMCP("MyCustomTools")

# 获取时间工具
@mcp.tool()
def get_current_time() -> str:
    """获取当前的系统时间""" # mcp读取的就是这个信息来判断是否调用的
    return f"当前时间是: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

# 必须有这个入口
if __name__ == "__main__":
    mcp.run(transport='stdio')

