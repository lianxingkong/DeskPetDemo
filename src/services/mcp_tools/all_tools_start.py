from mcp.server import FastMCP
from get_time import get_current_time
from get_weather import get_current_weather

mcp = FastMCP("MyCustomTools")

if __name__ == "__main__":
    mcp.add_tool(get_current_time)
    mcp.add_tool(get_current_weather)
    mcp.run(transport='stdio')