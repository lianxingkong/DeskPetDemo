from .example_mcp_config import *
from .multi_mcp_manager import *
from .. import app_config

if app_config.mcp.is_enable:
    mcp_manager = MultiMCPManager()
else:
    mcp_manager = None


from ..mcp_base import base_mcp_tools
@base_mcp_tools.BaseMcpStart
async def mcp_start():
    if app_config.mcp.is_enable:
        global mcp_manager
        await mcp_manager.connect_all()

@base_mcp_tools.BaseMcpEnd
async def mcp_stop():
    if app_config.mcp.is_enable:
        global mcp_manager
        await mcp_manager.connect_all()