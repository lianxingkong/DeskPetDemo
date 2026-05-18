import os

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QMovie, QImage
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QLineEdit, QPushButton, QFileDialog

from src.services.call_openai_tools import ChatToAI
from src.services.faster_whisper_tools import WhisperSegment
from src.services.get_voice_tools import get_voice_tools
from src.services.photo_handle_tools import Report_request
from src.ui.rewrite_getph_ui import ChatBox


class DeskpetUI(QWidget):
    # UI 发送消息的信号
    text_message_sent = pyqtSignal(str)  # 传递文字
    voice_data_ready = pyqtSignal(object)  # 传递录音的 numpy 数组
    photo_msg = pyqtSignal(object) # 传递获取到的图片地址

    def __init__(self):
        super().__init__()

        # 记录拖拽位置
        self.drag_pos = 0

        # 初始化图片状态
        self.pending_photo_desc = None

        # 获取当前文件的父级文件
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.img_path = os.path.join(current_dir, '..', 'resources', 'krx.gif')

        # 初始化UI
        self.init_ui()

        # 初始化线程 (必须在 UI 初始化之后，因为要操作按钮等控件)
        self.init_text_thread()
        self.init_voice_thread()
        self.init_photo_thread()

    def init_ui(self):
        # 创建窗口(无边框、置顶、背景透明)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 创建并导入GIF
        self.pixmap = QMovie(self.img_path)
        self.sticker = QLabel(self)
        self.sticker.setMovie(self.pixmap)
        self.pixmap.start()

        # 用户输入框
        self.input_msg = QLineEdit(self)
        self.input_msg.setPlaceholderText("请输入文本")

        # 创建输入确定按钮
        self.yes_botton = QPushButton("文字确认", self)
        self.yes_botton.clicked.connect(self.isInputMessage)

        # 创建语音输入确定按钮
        self.yes_voice_button = QPushButton("语音输入", self)
        self.yes_voice_button.clicked.connect(self.start_recording)  # 绑定到录音方法

        # 创建图片输入框
        self.btn_send_img = ChatBox()
        self.btn_send_img.setPlaceholderText("图片")

        # 创建图片输入确认按钮
        self.yes_photo_botton = QPushButton("图片确认",self)
        self.yes_photo_botton.clicked.connect(self.insert_local_image)  # 绑定到获取图片方法

        # 结果输出框
        self.output_msg = QLabel("", self)
        self.output_msg.setFont(QFont("Arial", 12))
        self.output_msg.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 200);
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 8px;
            }
        """)

        # 排布组件位置
        layout = QVBoxLayout()
        layout.addWidget(self.output_msg, 0, Qt.AlignCenter)
        layout.addWidget(self.sticker, 0, Qt.AlignCenter)
        layout.addWidget(self.input_msg, 0, Qt.AlignCenter)
        layout.addWidget(self.yes_botton, 0, Qt.AlignCenter)
        layout.addWidget(self.yes_voice_button, 0, Qt.AlignCenter)
        layout.addWidget(self.btn_send_img, 0, Qt.AlignCenter)
        layout.addWidget(self.yes_photo_botton, 0, Qt.AlignCenter)
        self.setLayout(layout)

        # 自适应图片大小
        self.sticker.adjustSize()
        # 自动调整窗口大小适应内容
        self.adjustSize()

    def init_text_thread(self):
        """初始化文本请求的子线程"""
        self.text_thread = QThread()
        self.chat_worker = ChatToAI()

        # 将工作对象移动到子线程
        self.chat_worker.moveToThread(self.text_thread)

        # 连接信号与槽 (注意信号名字对应)
        self.text_message_sent.connect(self.chat_worker.fetch_data)
        self.chat_worker.message_received.connect(self.update_output_msg)
        self.chat_worker.finished.connect(self.on_api_finished)

        # 启动线程
        self.text_thread.start()

    def init_voice_thread(self):
        """初始化语音识别的子线程"""
        self.voice_thread = QThread()
        self.voice_worker = WhisperSegment()
        # 将工作对象移动到子线程
        self.voice_worker.moveToThread(self.voice_thread)
        # 连接信号与槽
        self.voice_data_ready.connect(self.voice_worker.fasterWhisperSegment)
        # 状态信息连接（如"识别中..."）
        self.voice_worker.message_received.connect(self.update_output_msg)
        # 识别结果连接 -> 交给 AI 处理
        self.voice_worker.result_finished.connect(self.handle_voice_result)
        # 错误或未听清时的结束信号连接
        self.voice_worker.finished.connect(self.on_api_finished)
        # 线程启动时，自动触发加载模型
        self.voice_thread.started.connect(self.voice_worker.load_model)
        # 启动线程
        self.voice_thread.start()

    def init_photo_thread(self):
        """初始化图片处理的子线程"""
        self.photo_thread = QThread()
        self.photo_worker = Report_request()

        # 将工作对象移动到子线程
        self.photo_worker.moveToThread(self.photo_thread)
        # 连接信号与槽
        self.photo_msg.connect(self.photo_worker.start_process)
        # 状态信息连接
        self.photo_worker.img_received.connect(self.update_output_msg)
        # 识别结果连接
        self.photo_worker.img_finished.connect(self.handle_photo_result)
        self.photo_worker.finished.connect(self.on_api_finished)
        # 启动线程
        self.photo_thread.start()

    # 对于同一张图片，在不删除图片的基础上让以后的对话都可以继承图片信息
    def isInputMessage(self):
        """文字确认按钮点击触发，包括对图片的历届"""
        msg = self.input_msg.text()
        if not msg:
            self.output_msg.setText("你还什么都没有输入呢")
            return
        self.output_msg.setText("思考ing...\n")
        self.yes_botton.setEnabled(False)

        # 如果有等待中的图片描述，组合发送
        if self.pending_photo_desc:
            full_msg = f"图片内容：{self.pending_photo_desc}\n用户问题：{msg}\n"
        else:
            full_msg = msg

        self.text_message_sent.emit(full_msg)

    def start_recording(self):
        """语音按钮点击触发：录音并发射数据"""
        self.yes_voice_button.setEnabled(False)
        self.output_msg.setText("正在录音(5秒)...\n")

        # 录音结束后，拿到 numpy 数组
        audio_np = get_voice_tools(duration=5)

        # 发射信号，把 numpy 数组传给子线程去识别
        self.voice_data_ready.emit(audio_np)

    def insert_local_image(self):
        """图片按钮点击触发"""
        self.yes_photo_botton.setEnabled(False)

        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            image = QImage(file_path)
            if not image.isNull():
                # 获取当前光标并插入图片
                cursor = self.btn_send_img.textCursor()
                cursor.insertImage(image)
        # 发射信号，将图片地址传回去
        self.photo_msg.emit(file_path)

    def handle_voice_result(self, text):
        """处理语音识别出的最终文本，将其作为输入发送给 AI"""
        # 在界面上显示你说了什么
        current_text = self.output_msg.text()
        self.output_msg.setText(current_text + f"\n你(语音)：{text}\n")

        # 提示 AI 正在思考
        self.update_output_msg("AI思考ing...\n")

        # 发射信号给 chat_worker，请求 API（和文字输入走同一条路）
        self.text_message_sent.emit(text)

    def handle_photo_result(self, img):
        """图片识别完成，保存结果，等待用户输入问题"""
        # 保存图片描述，不立即发送
        self.pending_photo_desc = img
        # 提示用户输入问题
        current_text = self.output_msg.text()
        self.output_msg.setText(current_text + "\n图片已识别，请输入你想问的问题，点击文字确认发送\n")
        # 恢复按钮，让用户可以输入并点击确认
        self.yes_botton.setEnabled(True)
        self.yes_photo_botton.setEnabled(True)

    def on_api_finished(self):
        """语音结束后的清理工作"""
        self.yes_botton.setEnabled(True)  # 恢复文字按钮
        self.yes_voice_button.setEnabled(True)  # 恢复语音按钮
        self.yes_photo_botton.setEnabled(True)  # 回复图片按钮

    def update_output_msg(self, chunk_text):
        """统一更新 UI 文本的槽函数"""
        current_text = self.output_msg.text()
        self.output_msg.setText(current_text + chunk_text)

    # --- 鼠标事件重写 ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(Qt.ArrowCursor)

    def closeEvent(self, event):
        """安全退出线程"""
        self.text_thread.quit()
        self.text_thread.wait()
        self.voice_thread.quit()
        self.voice_thread.wait()
        event.accept()

