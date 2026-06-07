import sounddevice as sd
import numpy as np
import threading
from loguru import logger


class AsyncVoiceRecorder:
    """基于回调的非阻塞录音器（无 PyQt 依赖）"""

    def __init__(self, duration=5, fs=16000,
                 on_data_ready=None):
        self.stream = None
        self.duration = duration
        self.fs = fs
        self.frames_needed = int(duration * fs)
        self.recorded_frames = []
        self._lock = threading.Lock()
        self._timer = None
        self._recording = False

        # 回调替代 pyqtSignal
        self.on_data_ready = on_data_ready

    @property
    def is_recording(self):
        return self._recording

    def start_recording(self):
        """开始录音（非阻塞，瞬间返回）"""
        with self._lock:
            self.recorded_frames = []
            self._recording = True

        self.stream = sd.InputStream(
            samplerate=self.fs,
            channels=1,
            dtype='float32',
            callback=self._audio_callback
        )
        self.stream.start()

        logger.debug("开始录音")

        # threading.Timer 替代 QTimer，时间到自动调用 stop_recording
        self._timer = threading.Timer(self.duration, self.stop_recording)
        self._timer.daemon = True
        self._timer.start()

    def _audio_callback(self, indata, frames, time, status):
        """底层音频缓冲区满时自动调用（sounddevice 后台线程）"""
        if status:
            logger.warning(f"录音状态: {status}")
        with self._lock:
            self.recorded_frames.append(indata.copy())

    def stop_recording(self):
        """停止录音并回调数据"""
        logger.debug("已经进入 stop_recording")

        # 防止重复调用
        if not self._recording:
            return
        self._recording = False

        # 取消定时器（手动提前停止时需要）
        if self._timer:
            self._timer.cancel()
            self._timer = None

        if self.stream and self.stream.active:
            self.stream.stop()
            self.stream.close()

            with self._lock:
                frames = list(self.recorded_frames)

            if frames:
                audio_data = np.concatenate(frames, axis=0).flatten()
                data = audio_data[:self.frames_needed]
                self._emit_data(data)
                logger.debug("已经获取到数据，正在回调")


    def _emit_data(self, data):
        logger.debug(self.on_data_ready.__name__)
        if self.on_data_ready:
            self.on_data_ready(data)
