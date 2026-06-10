import asyncio
import base64
from pathlib import Path
from typing import Any, Coroutine

import aiohttp
from loguru import logger

from .config import app_config
from src.core.methods_tools import BaseAIRetry


save_dir = Path("/")
save_dir.mkdir(parents=True, exist_ok=True)

@BaseAIRetry(max_frequency=3, delay=0)
async def query_task_result(access_token: str, task_id: str):
    """查询任务结果"""
    params = {"access_token": access_token}
    data = {"task_id": task_id}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        async with session.post(app_config.baidu.get_result_url, params=params, json=data) as resp:
            result = await resp.json()
            logger.debug(f"查询任务返回：{result}")

            if "error_code" in result:
                raise Exception(f"查询任务失败：{result}")
            if "result" not in result:
                raise Exception(f"查询任务返回结构异常：{result}")

            return result["result"]


class Report_request():

    def __init__(self):
        super().__init__()
        self.monitor_status = False
        self.status = "img"
        self.img_url = None
        self.task_id = None

    async def start_process(self, img_queue, result_queue):
        """启动图片识别的中继"""
        try:
            while True:
                file_path = await img_queue.get()   # 常规返回图片地址，监听返回列表 [path, None, st:bool = True]
                if file_path:
                    await self.get_reply(result_queue, file_path)
                img_queue.task_done()
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(e)


    async def get_baidu_access_token(self, api_key, api_secret):
        # 修复：使用固定的 BAIDU_TOKEN_URL，而不是 report_url
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(app_config.baidu.token_url, params=params) as resp:
                data = await resp.json()
                if "access_token" not in data:
                    raise Exception(f"获取token失败：{data}")
                return data["access_token"]


    @BaseAIRetry(max_frequency=3, delay=0)
    async def post_access_token(self, request_url: str, image_base64: str, st: bool) -> tuple[Any, bool]:
        """
        提交百度图像内容理解异步任务
        """
        # 正常途径的提示词
        data = {
            "image": image_base64,
            "question": "请识别图片内容：若图片包含代码，请原样提取输出；若为其他内容，请详细客观描述。要求精准无冗余。",
        }

        # 用于监听屏幕的提示词
        data_demo = {
            "image": image_base64,
            "question": "请识别截图中的活跃应用名称或者游戏名称，并判断用户当前的操作状态。",
        }

        if st:
            # 命中监听渠道
            data = data_demo

        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
                async with session.post(request_url, json=data) as resp:
                    result = await resp.json()
                    logger.debug(f"百度提交接口返回：{result}")

                    if "error_code" in result:
                        error_code = result["error_code"]
                        error_msg = result.get("error_msg", "未知错误")
                        raise Exception(f"百度接口报错，错误码：{error_code}，错误信息：{error_msg}")

                    if "result" not in result or "task_id" not in result["result"]:
                        raise Exception(f"接口返回格式异常，未获取到task_id，完整返回：{result}")

                    self.task_id = result["result"]["task_id"]
                    logger.debug(f"图像理解任务提交成功，task_id：{self.task_id}")

        except Exception as e:
            logger.error(f"提交百度图像理解任务失败：{str(e)}")
            raise
        return self.task_id, st


    async def get_reply(self, queue, list):
        """
        获取百度图像内容理解结果异步任务
        """
        # 只获取一次token
        file_path = list[0]
        self.monitor_status = list[2]    # False 表示正常渠道，True 表示监听渠道

        access_token = await self.get_baidu_access_token(app_config.baidu.api_key, app_config.baidu.secret_key)
        logger.debug(f"获取到的access_token前20位: {access_token[:20] if access_token else 'None'}")

        # 正确的业务接口URL拼接 (这里用环境变量里的 report_url 才对)
        request_url = f"{app_config.baidu.report_url}?access_token={access_token}"

        # 读取图片并转换为base64
        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()
                if len(image_bytes) == 0:
                    logger.error("图片文件为空")
                    return

                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                logger.debug(f"图片base64编码长度: {len(image_base64)}")

                if len(image_base64) < 100:
                    logger.error("图片base64编码异常")
                    return
        except Exception as e:
            logger.error(f"读取图片文件失败: {e}")
            return

        # 提交任务
        try:
            task_id, st = await self.post_access_token(request_url, image_base64, self.monitor_status)
            logger.debug(f"提交成功，task_id: {task_id}")
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            return

        # 循环查询任务结果
        max_retry = 15
        retry_count = 0
        reply = None

        while retry_count < max_retry:
            try:
                task_result = await query_task_result(access_token, task_id)
                ret_code = task_result.get("ret_code", -1)

                if ret_code == 0:
                    reply = task_result.get("description", "无返回结果")
                    break
                elif ret_code == 1:
                    logger.debug(f"任务处理中，第{retry_count + 1}次重试")
                    await asyncio.sleep(2)
                    retry_count += 1
                else:
                    error_msg = task_result.get("error_msg", "未知错误")
                    logger.error(f"任务执行失败，ret_code: {ret_code}, error_msg: {error_msg}")
                    return
            except Exception as e:
                logger.error(f"查询任务结果失败: {e}")
                await asyncio.sleep(2)
                retry_count += 1

        if not reply:
            logger.error("任务处理超时，请重试")
            return
        logger.debug(f"baidu: {reply}")
        await queue.put((reply, self.status, st))  # 返回结果
