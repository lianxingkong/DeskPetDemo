from PyQt5 import uic
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QMovie, QImage
from PyQt5.QtWidgets import QWidget, QFileDialog
from loguru import logger

from src.core.rewrite_Function import ChatBox, MouseEvent
from src.ui.config import ui_setting


class DeskpetUI(QWidget, MouseEvent):
    # 1. 定义给管家的信号 (携带数据)
    text_input_confirmed = pyqtSignal(str) # 确认输入的文字
    image_selected = pyqtSignal(str)       # 选择的本地图片路径
    voice_record_triggered = pyqtSignal()  # 点击了语音按钮

    def __init__(self):
        super().__init__()
        uic.loadUi(ui_setting.ui.loadUi, self)
        self.drag_pos = 0
        self.img_path = ui_setting.ui.img_path
        self.setup_ui()

    def setup_ui(self):
        # 窗口属性
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # GIF
        self.pixmap = QMovie(self.img_path)
        self.petGIF.setMovie(self.pixmap)
        self.pixmap.start()

        # 文本框样式
        self.answerLogs.setReadOnly(True)
        self.answerLogs.setFont(QFont("Arial", 12))
        self.answerLogs.setStyleSheet("""...""")

        # 替换图片输入框
        h_layout = self.imageLogs.parent().layout()
        self.btn_send_img = ChatBox(self)
        self.btn_send_img.setPlaceholderText("图片输入框")
        self.btn_send_img.setMaximumHeight(100)
        h_layout.replaceWidget(self.imageLogs, self.btn_send_img)
        self.imageLogs.hide()
        self.imageLogs.deleteLater()

        # 2. 绑定原生按钮点击 -> 发射自定义信号
        self.yesButton.clicked.connect(self._on_yes_clicked)
        self.imageButton.clicked.connect(self._on_image_clicked)
        self.voiceBotton.clicked.connect(self._on_voice_clicked)

    def _on_voice_clicked(self):
        """语音按钮点击触发"""
        self.voiceBotton.setEnabled(False)
        logger.debug("UI: 语音按钮被点击，发射信号")
        self.voice_record_triggered.emit()

    def _on_yes_clicked(self):
        """确认按钮被点击，取文字发射出去"""
        msg = self.inputLogs.text()
        if not msg:
            self.show_system_message("你还什么都没有输入呢")
            return
        self.text_input_confirmed.emit(msg)

    def _on_image_clicked(self):
        """图片按钮被点击，选文件发射出去"""
        file_path, _ = QFileDialog.getOpenFileName(self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            image = QImage(file_path)
            if not image.isNull():
                cursor = self.btn_send_img.textCursor()
                cursor.insertImage(image)
            self.image_selected.emit(file_path)

    # ===== 提供给管家调用的更新方法 =====
    def show_system_message(self, text):
        self.answerLogs.setText(text)

    def append_response_chunk(self, chunk_text):
        cursor = self.answerLogs.textCursor()
        cursor.movePosition(cursor.End)
        cursor.insertText(chunk_text)
        self.answerLogs.setTextCursor(cursor)
        self.answerLogs.ensureCursorVisible()

    def set_loading_state(self, is_loading):
        """统一控制按钮的可用状态"""
        self.yesButton.setEnabled(not is_loading)
        self.voiceBotton.setEnabled(not is_loading)
        self.imageButton.setEnabled(not is_loading)
        if is_loading:
            self.answerLogs.setText("思考ing...\n")
