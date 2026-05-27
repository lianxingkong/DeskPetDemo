from .example_mcp_config import *
from .MultiMCPManager import *
from .. import app_config

if app_config.mcp.is_enable:
    mcp_manager = MultiMCPManager()
else:
    mcp_manager = None


from ..mcp_services import base_mcp_tools
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