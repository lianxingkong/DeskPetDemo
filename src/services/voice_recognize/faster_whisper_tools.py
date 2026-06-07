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
        """接收音频数据并进行识别"""
        audio_data = await ccb_queue.get()
        if self.model is None:
            logger.error("语音模型未加载成功，无法识别！")
            return

        try:
            logger.info("语音识别中")
            segments, info = self.model.transcribe(audio_data, beam_size=5)

            # 拼接识别结果
            result_text = "".join(segment.text for segment in segments).strip()

            if result_text:
                # 如果有结果，发射 result_finished 信号，把识别的文字传出去
                logger.info(f"获取到的结果{result_text}")
                await queue.put((result_text, None))
            else:
                logger.error("[未听清] 没有检测到有效语音。")

        except Exception as e:
            logger.error(e)

