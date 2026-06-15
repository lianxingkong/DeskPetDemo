from mcp.server import FastMCP
from get_time import get_current_time
from get_weather import get_current_weather
from get_music import get_bilibili_music


mcp = FastMCP("MyCustomTools")

if __name__ == "__main__":
    mcp.add_tool(get_current_time)
    mcp.add_tool(get_current_weather)
    mcp.add_tool(get_bilibili_music)
    mcp.run(transport='stdio')