import asyncio
import base64
import os
import time
from pathlib import Path

import aiohttp
import httpx
from PyQt5.QtCore import pyqtSignal, QObject
from loguru import logger

from ..image_recognize_services import *


async def query_task_result(access_token: str, task_id: str):
    """查询任务结果"""
    params = {"access_token": access_token}
    data = {"task_id": task_id}
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
        async with session.post(get_result_url, params=params, json=data) as resp:
            result = await resp.json()
            logger.debug(f"查询任务返回：{result}")

            if "error_code" in result:
                raise Exception(f"查询任务失败：{result}")
            if "result" not in result:
                raise Exception(f"查询任务返回结构异常：{result}")

            return result["result"]


class Report_request(QObject):
    # 定义信号
    img_received = pyqtSignal(str)  # 用于发送中间状态
    img_finished = pyqtSignal(str)  # 用于发送最终的识别结果文本
    finished = pyqtSignal()         # 任务结束信号

    def __init__(self):
        super().__init__()
        self.img_url = None
        self.task_id = None
        self.save_path = None

    def start_process(self, file_path):
        """供 PyQt 信号调用的同步入口方法"""
        # 如果传进来的是本地路径（用户选的文件），直接赋值给 save_path
        if file_path and os.path.exists(file_path):
            self.save_path = Path(file_path)
            self.img_url = None  # 本地文件不需要下载
        else:
            self.img_url = file_path  # 如果是网络地址才需要下载

        # 在子线程中启动异步事件循环
        try:
            asyncio.run(self._async_pipeline())
        except Exception as e:
            logger.error(f"图片处理异步流程报错: {e}")
            self.img_finished.emit("图片识别失败")
            self.finished.emit()

    async def _async_pipeline(self):
        """异步流水线：根据情况下载或直接识别"""
        # 如果是网络地址，才执行下载
        if self.img_url and not self.save_path:
            await self.give_photo_url()

        # 执行核心识别逻辑
        await self.get_reply()

    async def get_baidu_access_token(self, api_key, api_secret):
        # 修复：使用固定的 BAIDU_TOKEN_URL，而不是 report_url
        params = {
            "grant_type": "client_credentials",
            "client_id": api_key,
            "client_secret": api_secret
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, params=params) as resp:
                data = await resp.json()
                if "access_token" not in data:
                    raise Exception(f"获取token失败：{data}")
                return data["access_token"]

    # 下载图片
    async def photo_download(self, img_url, save_path: Path):
        if img_url is None:
            self.img_received.emit("图片获取失败")
            return
        async with httpx.AsyncClient(headers={}, timeout=60, max_redirects=5) as client_httpx:
            async with client_httpx.stream("GET", img_url) as resp:
                try:
                    resp.raise_for_status()
                    with open(save_path, "wb") as f:
                        async for chunk in resp.aiter_bytes():
                            f.write(chunk)
                except Exception as e:
                    logger.error(e)

    async def post_access_token(self, request_url: str, image_base64: str) -> str:
        """
        提交百度图像内容理解异步任务
        """
        data = {
            "image": image_base64,
            "question": "请识别图片内容：若图片包含代码，请原样提取输出；若为其他内容，请详细客观描述。要求精准无冗余。",
        }
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
        return self.task_id

    async def give_photo_url(self):
        """下载图片"""
        file_name = f"{time.strftime('%Y%m%d_%H%M%S', time.localtime())}.jpg"
        self.save_path = save_dir / file_name
        await self.photo_download(self.img_url, self.save_path)

    async def get_reply(self):
        """核心识别逻辑"""
        # 只获取一次token
        access_token = await self.get_baidu_access_token(api_key, secret_key)
        logger.debug(f"获取到的access_token前20位: {access_token[:20] if access_token else 'None'}")

        # 正确的业务接口URL拼接 (这里用环境变量里的 report_url 才对)
        request_url = f"{report_url}?access_token={access_token}"

        # 读取图片并转换为base64
        try:
            with open(self.save_path, "rb") as f:
                image_bytes = f.read()
                if len(image_bytes) == 0:
                    logger.error("图片文件为空")
                    self.finished.emit()
                    return

                image_base64 = base64.b64encode(image_bytes).decode('utf-8')
                logger.debug(f"图片base64编码长度: {len(image_base64)}")

                if len(image_base64) < 100:
                    logger.error("图片base64编码异常")
                    self.finished.emit()
                    return
        except Exception as e:
            logger.error(f"读取图片文件失败: {e}")
            self.finished.emit()
            return

        # 提交任务
        try:
            task_id = await self.post_access_token(request_url, image_base64)
            logger.debug(f"提交成功，task_id: {task_id}")
        except Exception as e:
            logger.error(f"提交任务失败: {e}")
            self.finished.emit()
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
                    self.finished.emit()
                    return
            except Exception as e:
                logger.error(f"查询任务结果失败: {e}")
                await asyncio.sleep(2)
                retry_count += 1

        if not reply:
            logger.error("任务处理超时，请重试")
            self.finished.emit()
            return
        logger.debug(f"baidu: {reply}")
        self.img_finished.emit(reply)
        self.finished.emit()
