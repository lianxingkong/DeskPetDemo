import asyncio  # 需要引入 asyncio
from faster_whisper import WhisperModel
from loguru import logger


class WhisperSegment():

    def __init__(self):
        super().__init__()
        self.model = None

    async def load_model(self):
        """加载模型"""
        if self.model is None:
            try:
                logger.info("正在加载语音识别模型(首次运行需下载)，请稍候...")
                self.model = WhisperModel("base", device="cpu", compute_type="int8")
                logger.info("模型加载完成！")
            except Exception as e:
                logger.error(f"模型加载失败: {e}")
                self.model = None

    async def fasterWhisperSegment(self, queue, ccb_queue):
        """接收音频数据并进行识别（常驻消费）"""
        while True:  # ★ 核心修复1：必须加 while True 保持常驻监听
            audio_data = await ccb_queue.get()

            if self.model is None:
                logger.error("语音模型未加载成功，无法识别！")
                continue  # 模型没加载就跳过，继续监听下一个

            try:
                logger.info("语音识别中")

                # ★ 核心修复2：将 CPU 密集型的同步阻塞操作放入线程池，防止卡死事件循环
                def _do_transcribe():
                    segments, info = self.model.transcribe(audio_data, beam_size=5)
                    # 拼接识别结果 (在子线程中完成迭代和拼接)
                    return "".join(segment.text for segment in segments).strip()

                result_text = await asyncio.to_thread(_do_transcribe)

                if result_text:
                    logger.info(f"获取到的结果{result_text}")
                    await queue.put((result_text, None, False))
                else:
                    logger.error("[未听清] 没有检测到有效语音。")

            except Exception as e:
                logger.error(f"语音识别出错: {e}")

