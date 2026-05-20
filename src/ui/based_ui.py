import os

from PyQt5 import uic
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QMovie, QImage
from PyQt5.QtWidgets import QWidget, QFileDialog

from src.core.rewrite_Function.rewrite_mouseEvent import MouseEvent
from src.core.rewrite_Function.rewrite_getph_ui import ChatBox
from src.services import ChatToAI, WhisperSegment, get_voice_tools, Report_request

from .config import ui_setting


class DeskpetUI(QWidget,MouseEvent):
    # UI 发送消息的信号
    text_message_sent = pyqtSignal(str)  # 传递文字
    voice_data_ready = pyqtSignal(object)  # 传递录音的 numpy 数组
    photo_msg = pyqtSignal(object)  # 传递获取到的图片地址

    def __init__(self):
        super().__init__()
        # 初始化自定义的ui
        uic.loadUi(ui_setting.ui.loadUi, self)
        # 记录拖拽位置
        self.drag_pos = 0
        # 初始化图片状态
        self.pending_photo_desc = None
        # 获取当前文件的父级文件
        self.img_path = ui_setting.ui.img_path
        # 初始化UI
        self.init_ui()
        # 初始化线程
        self.init_text_thread()
        self.init_voice_thread()
        self.init_photo_thread()

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

        # 3. 替换 imageLogs 为自定义的 ChatBox
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

    def isInputMessage(self):
        """文字确认按钮点击触发"""
        msg = self.inputLogs.text()
        if not msg:
            self.answerLogs.setText("你还什么都没有输入呢")
            return
        self.answerLogs.setText("思考ing...\n")
        self.yesButton.setEnabled(False)

        if self.pending_photo_desc:
            full_msg = f"图片内容：{self.pending_photo_desc}\n用户问题：{msg}\n"
        else:
            full_msg = msg

        self.text_message_sent.emit(full_msg)

    def start_recording(self):
        """语音按钮点击触发"""
        self.voiceBotton.setEnabled(False)
        self.answerLogs.setText("正在录音(5秒)...\n")
        audio_np = get_voice_tools(duration=5)
        self.voice_data_ready.emit(audio_np)

    def insert_local_image(self):
        """图片按钮点击触发"""
        self.imageButton.setEnabled(False)
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            image = QImage(file_path)
            if not image.isNull():
                cursor = self.btn_send_img.textCursor()
                cursor.insertImage(image)
        self.photo_msg.emit(file_path)

    def handle_voice_result(self, text):
        """处理语音识别出的最终文本"""
        current_text = self.answerLogs.toPlainText()
        self.answerLogs.setText(current_text + f"\n你(语音)：{text}\n")
        self.update_output_msg("AI思考ing...\n")
        self.text_message_sent.emit(text)

    def handle_photo_result(self, img):
        """图片识别完成，保存结果"""
        self.pending_photo_desc = img
        current_text = self.answerLogs.toPlainText()
        self.answerLogs.setText(current_text + "\n图片已识别，请输入你想问的问题，点击文字确认发送\n")
        self.yesButton.setEnabled(True)
        self.imageButton.setEnabled(True)

    def on_api_finished(self):
        """请求结束后的清理工作"""
        self.yesButton.setEnabled(True)
        self.voiceBotton.setEnabled(True)
        self.imageButton.setEnabled(True)

    def update_output_msg(self, chunk_text):
        """统一更新 UI 文本的槽函数 (使用光标插入，对流式输出更友好)"""
        cursor = self.answerLogs.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(chunk_text)
        self.answerLogs.setTextCursor(cursor)
        self.answerLogs.ensureCursorVisible()  # 自动滚动到最底部

    def closeEvent(self, event):
        """安全退出线程"""
        self.text_thread.quit()
        self.text_thread.wait()
        self.voice_thread.quit()
        self.voice_thread.wait()
        self.photo_thread.quit()
        self.photo_thread.wait()
        event.accept()
