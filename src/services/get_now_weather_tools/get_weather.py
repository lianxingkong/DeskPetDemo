import time
from datetime import date

import httpx
from loguru import logger
from mcp.server.fastmcp import FastMCP

from config import app_config
from method import build_headers

# 初始化服务器
mcp = FastMCP("MyCustomTools")

# 获取天气工具
@mcp.tool()
async def get_current_weather(location : str):
    """获取指定地点的天气。

    Args:
        location: 城市名称，如：北京、上海、抚州（不要带"市"字）
    """
    logger.debug(app_config.yaohu.api_key)
    # 获取当前时间戳
    timestamp = int(time.time())
    result = {}
    if app_config.yaohu.api_key is None:
        logger.error("妖狐数据的key为空")
        return "妖狐数据的key为空"

    url = f"https://api.yaohud.cn/api/v6/weather?"

    headers = build_headers(timestamp)

    params = {
        "key": app_config.yaohu.api_key,
        "location": location
    }

    async with httpx.AsyncClient(timeout=120) as client:
        try:
            response = await client.get(url=url,headers=headers, params=params)
            result = response.json()
            logger.debug(result)
        except httpx.HTTPError as e:
            logger.error(e)
            return "妖狐数据请求错误"

    logger.info(f"API状态码: {response.status_code}")
    logger.info(f"API原始返回: {response.text}")

    today = date.today().day
    city = result["data"]["location_info"]["city"]
    wendu = result["data"]["weather_data"]["wendu"]
    quality = result["data"]["weather_data"]["quality"]

    answer = {
        "today": today,
        "city": city,
        "wendu": wendu,
        "quality": quality,
    }

    logger.debug(answer)

    return answer

# 必须有这个入口
if __name__ == "__main__":
    mcp.run(transport='stdio')
