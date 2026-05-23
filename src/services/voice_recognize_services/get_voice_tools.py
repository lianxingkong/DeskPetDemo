import sounddevice as sd
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from loguru import logger


class AsyncVoiceRecorder(QObject):
    """(AI)基于回调的非阻塞录音器（真正的异步）"""
    voice_data_ready = pyqtSignal(object)
    recording_status = pyqtSignal(str)

    def __init__(self, duration=5, fs=16000):
        super().__init__()
        self.duration = duration
        self.fs = fs
        self.frames_needed = int(duration * fs)
        self.recorded_frames = []

        # 使用 QTimer 来控制录音时长，不阻塞线程
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.stop_recording)

    def start_recording(self):
        """开始录音（非阻塞，瞬间返回）"""
        self.recorded_frames = []
        self.recording_status.emit(f"正在录音({self.duration}秒)...")

        # 开启 InputStream，底层自动在后台采集音频
        self.stream = sd.InputStream(
            samplerate=self.fs,
            channels=1,
            dtype='float32',
            callback=self._audio_callback  # 核心：数据就绪时的回调
        )
        self.stream.start()

        # 启动定时器，时间一到自动停止
        self.timer.start(int(self.duration * 1000))

    def _audio_callback(self, indata, frames, time, status):
        """底层音频缓冲区满时自动调用（在后台线程执行）"""
        if status:
            logger.warning(f"录音状态: {status}")
        self.recorded_frames.append(indata.copy())

    def stop_recording(self):
        """停止录音并发射数据"""
        if hasattr(self, 'stream') and self.stream.active:
            self.stream.stop()
            self.stream.close()

            # 将收集到的片段拼成一维 numpy 数组
            if self.recorded_frames:
                audio_data = np.concatenate(self.recorded_frames, axis=0).flatten()
                # 如果录音稍微超长，截断到指定时长
                self.voice_data_ready.emit(audio_data[:self.frames_needed])

            self.recording_status.emit("录音结束")
