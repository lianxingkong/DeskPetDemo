from PyQt5.QtCore import QObject, QThread, pyqtSignal
from src.services import ChatToAI, WhisperSegment, Report_request, HandleMemory, AsyncVoiceRecorder


class ThreadManager(QObject):
    # ===== 暴露给管家调用的信号 =====
    text_message_sent = pyqtSignal(str)
    voice_record_triggered = pyqtSignal()  # 触发录音的信号
    photo_msg = pyqtSignal(str)
    memory_msg = pyqtSignal(object)
    memory_query_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

        # 第一步：先实例化所有的 Worker (避免初始化顺序导致的找不到属性问题)
        self.chat_worker = ChatToAI()
        self.recorder_worker = AsyncVoiceRecorder(duration=5, fs=16000)  # 🚨 实例化录音器
        self.voice_worker = WhisperSegment()
        self.photo_worker = Report_request()
        self.memory_worker = HandleMemory()

        # 第三步：创建线程、移动Worker、启动线程
        self._init_text_thread()
        self._init_recorder_thread()
        self._init_voice_thread()
        self._init_photo_thread()
        self._init_memory_thread()

        # 第二步：跨线程的流水线信号连接 (录音完毕 -> 交给 Whisper)
        # 触发录音的信号 -> 录音器的启动方法
        self.voice_record_triggered.connect(self.recorder_worker.start_recording)
        self.recorder_worker.voice_data_ready.connect(self.voice_worker.fasterWhisperSegment)

    def _init_text_thread(self):
        self.text_thread = QThread()
        self.chat_worker.moveToThread(self.text_thread)
        self.text_message_sent.connect(self.chat_worker.fetch_data)
        self.text_thread.start()

    def _init_recorder_thread(self):
        self.recorder_thread = QThread()
        self.recorder_worker.moveToThread(self.recorder_thread)
        self.recorder_thread.start()

    def _init_voice_thread(self):
        self.voice_thread = QThread()
        self.voice_worker.moveToThread(self.voice_thread)
        self.voice_thread.started.connect(self.voice_worker.load_model)
        self.voice_thread.start()

    def _init_photo_thread(self):
        self.photo_thread = QThread()
        self.photo_worker.moveToThread(self.photo_thread)
        self.photo_msg.connect(self.photo_worker.start_process)
        self.photo_thread.start()

    def _init_memory_thread(self):
        self.memory_thread = QThread()
        self.memory_worker.moveToThread(self.memory_thread)
        self.memory_msg.connect(self.memory_worker.to_ai_memory)
        self.memory_query_signal.connect(self.memory_worker.query_memory)
        self.memory_thread.start()

    def cleanup(self):
        self.recorder_thread.quit()
        self.recorder_thread.wait()
        self.text_thread.quit()
        self.text_thread.wait()
        self.memory_thread.quit()
        self.memory_thread.wait()
        self.voice_thread.quit()
        self.voice_thread.wait()
        self.photo_thread.quit()
        self.photo_thread.wait()
