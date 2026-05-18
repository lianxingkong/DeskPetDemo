from PyQt5.QtCore import QObject, pyqtSignal
from faster_whisper import WhisperModel


class WhisperSegment(QObject):
    # 定义信号
    message_received = pyqtSignal(str)  # 用于发送中间状态（如"识别中"）
    result_finished = pyqtSignal(str)  # 用于发送最终的识别结果文本
    finished = pyqtSignal()  # 任务结束信号

    def __init__(self):
        super().__init__()
        self.model = None

    def load_model(self):
        """加载模型"""
        if self.model is None:
            try:
                print("正在加载语音识别模型(首次运行需下载)，请稍候...")
                self.model = WhisperModel("base", device="cpu", compute_type="int8")
                print("模型加载完成！")
            except Exception as e:
                print(f"模型加载失败: {e}")
                self.model = None

    def fasterWhisperSegment(self, audio_data):
        """接收音频数据并进行识别"""
        if self.model is None:
            self.message_received.emit("\n[错误] 语音模型未加载成功，无法识别！")
            self.finished.emit()
            return

        try:
            self.message_received.emit("语音识别中...\n")
            segments, info = self.model.transcribe(audio_data, beam_size=5)

            # 拼接识别结果
            result_text = "".join(segment.text for segment in segments).strip()

            if result_text:
                # 如果有结果，发射 result_finished 信号，把识别的文字传出去
                self.result_finished.emit(result_text)
                # 注意：识别成功时不在这里发 finished 信号，因为还要等 AI 回复完毕才算结束
            else:
                self.message_received.emit("\n[未听清] 没有检测到有效语音。")
                self.finished.emit()  # 没听清，流程结束，恢复按钮

        except Exception as e:
            self.message_received.emit(f"\n[识别错误] {str(e)}")
            self.finished.emit()  # 出错，流程结束，恢复按钮

