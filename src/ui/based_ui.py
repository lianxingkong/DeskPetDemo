from PyQt5 import uic
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QMovie, QImage
from PyQt5.QtWidgets import QWidget, QFileDialog
from loguru import logger

from src.core import ChatBox, MouseEvent
from src.services import ChatToAI, WhisperSegment,AsyncVoiceRecorder, Report_request, HandleMemory

from .config import ui_setting


class DeskpetUI(QWidget,MouseEvent):
    # UI 发送消息的信号
    text_message_sent = pyqtSignal(str)  # 传递文字
    voice_data_ready = pyqtSignal(object)  # 传递录音的 numpy 数组
    photo_msg = pyqtSignal(object)  # 传递获取到的图片地址
    memory_msg = pyqtSignal(object)
    memory_query_signal = pyqtSignal(str)  # 专门用于检索记忆的信号

    def __init__(self):
        super().__init__()
        # 初始化自定义的ui
        uic.loadUi(ui_setting.ui.loadUi, self)
        # 记录拖拽位置
        self.drag_pos = 0
        # 初始化图片状态,用于记录图片信息
        self.pending_photo_desc = None
        # 初始化图片和问题
        self.init_msg_desc = None
        # 初始化回复状态，用于记录回复信息
        self.pending_text_msg = ""
        # 获取当前文件的父级文件
        self.img_path = ui_setting.ui.img_path
        # 初始化UI
        self.init_ui()
        # 初始化检测对话状态
        self.init_check_status = 0
        # 初始化匹配到的记忆(如果存在)
        self.founded_msg = None
        # 初始化记录音频文本
        self.init_voices_text = None
        # 初始化异步录音器
        self.voice_recorder = AsyncVoiceRecorder(duration=5)
        self.voice_recorder.voice_data_ready.connect(self.on_voice_data_received)
        self.voice_recorder.recording_status.connect(self.answerLogs.setText)
        # 初始化线程
        self.init_text_thread()
        self.init_voice_thread()
        self.init_photo_thread()
        self.init_memory_thread()

    def init_ui(self):
        # 创建窗口(无边框、置顶、背景透明)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 1. petGIF (使用布局后，GIF会自动填满中间区域)
        self.pixmap = QMovie(self.img_path)
        self.petGIF.setMovie(self.pixmap)
        self.pixmap.start()

        # 2. answerLogs -> 输出框配置 (QTextEdit 只读模式)
        self.answerLogs.setReadOnly(True)
        self.answerLogs.setFont(QFont("Arial", 12))
        self.answerLogs.setStyleSheet("""
            QTextEdit {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 8px;
            }
        """)

        # 获取 imageLogs 所在的水平布局
        h_layout = self.imageLogs.parent().layout()
        self.btn_send_img = ChatBox(self)
        self.btn_send_img.setPlaceholderText("图片输入框")
        self.btn_send_img.setMaximumHeight(100)  # 限制图片输入框的高度，宽度会自适应拉宽
        # 在布局中替换占位控件
        h_layout.replaceWidget(self.imageLogs, self.btn_send_img)
        self.imageLogs.hide()
        self.imageLogs.deleteLater()  # 安全删除旧控件

        # 4. 按钮信号绑定
        self.yesButton.clicked.connect(self.isInputMessage)
        self.voiceBotton.clicked.connect(self.start_recording)
        self.imageButton.clicked.connect(self.insert_local_image)
        # 当输入框文本/内容发生变化时，自动检查是否有图片
        self.btn_send_img.textChanged.connect(self.check_image_status)

    def init_text_thread(self):
        """初始化文本请求的子线程"""
        self.text_thread = QThread()
        self.chat_worker = ChatToAI()
        self.chat_worker.moveToThread(self.text_thread)

        self.text_message_sent.connect(self.chat_worker.fetch_data)
        self.chat_worker.message_received.connect(self.update_output_msg)
        self.chat_worker.finished.connect(self.on_api_finished)

        self.text_thread.start()

    def init_voice_thread(self):
        """初始化语音识别的子线程"""
        self.voice_thread = QThread()
        self.voice_worker = WhisperSegment()
        self.voice_worker.moveToThread(self.voice_thread)

        self.voice_data_ready.connect(self.voice_worker.fasterWhisperSegment)
        self.voice_worker.message_received.connect(self.update_output_msg)
        self.voice_worker.result_finished.connect(self.handle_voice_result)
        self.voice_worker.finished.connect(self.on_api_finished)
        self.voice_thread.started.connect(self.voice_worker.load_model)

        self.voice_thread.start()

    def init_photo_thread(self):
        """初始化图片处理的子线程"""
        self.photo_thread = QThread()
        self.photo_worker = Report_request()
        self.photo_worker.moveToThread(self.photo_thread)

        self.photo_msg.connect(self.photo_worker.start_process)
        self.photo_worker.img_received.connect(self.update_output_msg)
        self.photo_worker.img_finished.connect(self.handle_photo_result)
        self.photo_worker.finished.connect(self.on_api_finished)

        self.photo_thread.start()

    def init_memory_thread(self):
        """初始化记忆处理的子线程"""
        self.memory_thread = QThread()
        self.memory_worker = HandleMemory()
        self.memory_worker.moveToThread(self.memory_thread)
        # 归档连接
        self.memory_msg.connect(self.memory_worker.to_ai_memory)
        self.memory_worker.finished.connect(self.on_memory_finished)
        # 检索连接
        self.memory_query_signal.connect(self.memory_worker.query_memory)
        self.memory_worker.query_result.connect(self.on_memory_query_result)

        self.memory_thread.start()

    def has_image_in_text_edit(self) -> bool:
        """判断输入框内是否包含图片"""
        doc = self.btn_send_img.document()
        block = doc.begin()
        # 遍历文档中的每一个段落
        while block.isValid():
            it = block.begin()
            # 遍历段落中的每一个片段
            while not it.atEnd():
                fragment = it.fragment()
                if fragment.isValid():
                    char_format = fragment.charFormat()
                    # 如果该片段是图片格式，说明有图片
                    if char_format.isImageFormat():
                        return True
                it += 1
            block = block.next()
        return False

    def check_image_status(self):
        """检测图片框内是否有图片"""
        has_img = self.has_image_in_text_edit()
        if not has_img:
            self.pending_photo_desc = None
        else:
            return

    def isInputMessage(self):
        """文字确认按钮点击触发"""
        msg = self.inputLogs.text()
        if not msg:
            self.answerLogs.setText("你还什么都没有输入呢")
            return

        # 先检索记忆，再发送（改为异步等待模式）
        self.pending_user_msg = msg
        self.answerLogs.setText("检索记忆中...\n")
        self.yesButton.setEnabled(False)

        # 发射检索信号，等检索完成后再真正发送
        self.memory_query_signal.emit(msg)

    def start_recording(self):
        """语音按钮点击触发"""
        self.voiceBotton.setEnabled(False)
        self.voice_recorder.start_recording()

    def on_voice_data_received(self, audio_np):
        """接收录音器传回来的音频数据（5秒后才会触发）"""
        self.voiceBotton.setEnabled(True)
        # 传递给whisper识别
        self.voice_data_ready.emit(audio_np)

    def insert_local_image(self):
        """图片按钮点击触发"""
        self.imageButton.setEnabled(False)
        # 阻断文字输入，等待图片处理
        self.yesButton.setEnabled(False)
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            image = QImage(file_path)
            if not image.isNull():
                cursor = self.btn_send_img.textCursor()
                cursor.insertImage(image)
        else:
            self.pending_photo_desc = None
        self.photo_msg.emit(file_path)

    def memory_handle_tools(self, msg, memory, group):
        """处理并传递记忆"""
        result = f"新的信息：{msg}\n记忆数据：{memory}\n组别：{group}"
        self.text_message_sent.emit(result)

    def handle_voice_result(self, text):
        """处理语音识别出的最终文本"""
        current_text = self.answerLogs.toPlainText()
        self.init_voices_text = text
        self.answerLogs.setText(current_text + f"\n你(语音)：{text}\n")
        self.answerLogs.setText("思考ing...\n")
        self.text_message_sent.emit(text)

    def handle_photo_result(self, img):
        """图片识别完成，保存结果"""
        self.pending_photo_desc = img
        current_text = self.answerLogs.toPlainText()
        self.answerLogs.setText(current_text + "\n图片已识别，请输入你想问的问题，点击文字确认发送\n")
        self.yesButton.setEnabled(True)
        self.imageButton.setEnabled(True)

    def on_memory_query_result(self, user_msg, matched_memory):
        """记忆检索完成，拼装最终消息并发送"""
        memory_prompt = ""
        if matched_memory and isinstance(matched_memory, dict):
            valid_memories = []
            for key, value in matched_memory.items():
                if isinstance(value, dict) and value.get("memory") and value.get("weight", 0) > 0:
                    valid_memories.append(f"[权重{value['weight']}分]{value['memory']}")
            if valid_memories:
                memory_prompt = "【相关记忆】\n" + "\n".join(valid_memories) + "\n"

        full_msg = f"{memory_prompt}【当前问题】{user_msg}" if memory_prompt else user_msg

        if self.pending_photo_desc:
            full_msg = f"图片内容：{self.pending_photo_desc}\n{full_msg}"

        self.init_msg_desc = full_msg
        self.answerLogs.setText("思考ing...\n")
        logger.debug(f"传递的信息{full_msg}")
        self.text_message_sent.emit(full_msg)
        self.founded_msg = None

    def on_api_finished(self):
        """请求结束后的清理工作，并自发触发记忆归档"""
        logger.info(f"回复信息：{self.pending_text_msg}")
        self.yesButton.setEnabled(True)
        self.voiceBotton.setEnabled(True)
        self.imageButton.setEnabled(True)

        # 自发触发记忆系统
        if self.init_msg_desc:
            user_input = self.init_msg_desc
        elif self.init_voices_text:
            user_input = self.init_voices_text
        else:
            user_input = self.inputLogs.text()
        self.init_voices_text = None
        ai_reply = self.pending_text_msg
        if self.init_check_status:  # 确保有输入和回复
            full_dialogue = f"用户问题：{user_input}\nAI回复：{ai_reply}"
            # 发射信号，将当前完整对话传给记忆系统
            self.memory_msg.emit(full_dialogue)

        # 清空暂存的回复,初始化检测对话状态
        self.pending_text_msg = ""
        self.init_check_status = 0

    def update_output_msg(self, chunk_text):
        """统一更新 UI 文本的槽函数 (使用光标插入，对流式输出更友好)"""
        # 这样子去拼接
        self.init_check_status = 1
        self.pending_text_msg = f"{self.pending_text_msg}{chunk_text}"
        cursor = self.answerLogs.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(chunk_text)
        self.answerLogs.setTextCursor(cursor)
        self.answerLogs.ensureCursorVisible()  # 自动滚动到最底部

    def on_memory_finished(self,msg):
        if msg:
            self.founded_msg = msg
            logger.info("已找到相同记忆，记忆已归档")

    def pass_memory_msg(self):
        """传递本次输入的问题和回复"""
        return f"问题是：{self.inputLogs.text()}\n回复是：{self.pending_text_msg}"

    def closeEvent(self, event):
        """安全退出线程"""
        self.text_thread.quit()
        self.text_thread.wait()
        self.voice_thread.quit()
        self.voice_thread.wait()
        self.photo_thread.quit()
        self.photo_thread.wait()
        self.memory_thread.quit()
        self.memory_thread.wait()
        event.accept()
